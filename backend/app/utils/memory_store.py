"""
长期记忆存储（LangGraph AsyncSqliteStore 封装）。

设计要点（docs/DESIGN_rerank_and_memory.md 方案 B）：
- 独立 DB 文件 STORE_DB，与 checkpoint 物理隔离，无写竞争
- 写入用规则优先 + LLM 兜底：省成本、行为可预期
- watch_stock 用确定性 key `watch:{stock_code}` 幂等去重
- 每用户上限 50 条，超出淘汰最旧
- 全链路 fail-open：Store 不可用时记忆缺失，不影响研究主流程
"""
import asyncio
import re
import uuid
from typing import Any, Dict, List, Optional

from app.config import STORE_DB
from app.utils.logger import get_logger

log = get_logger("memory_store")

MEMORY_NAMESPACE_PREFIX = "memories"
MAX_MEMORIES_PER_USER = 50
LOAD_LIMIT = 5  # 注入 prompt 的最大条数（前缀扫描取最近 N 条，非语义检索）

# S3 一致性：复用 report_ingest 的严格正则，不用 router 的宽松 \b\d{6}\b，
# 避免把日期段号、基金代码误记为 watch_stock
_STOCK_CODE_RE = re.compile(r'(?<!\d)([68]\d{5}|[03]\d{5})(?!\d)')
_WATCH_KEYWORD_RE = re.compile(r'(关注|记住|跟踪|研究|分析|看看)')
_REMEMBER_KEYWORD_RE = re.compile(r'记住|记一下|别忘了')

# 演示预置记忆（与 mock 快照同策略：避免演示时记忆为空显得功能没做）
DEMO_USER_ID = "default"
DEMO_MEMORIES = [
    {"kind": "watch_stock", "content": "用户长期关注复星医药(600196)", "stock_code": "600196",
     "source": "auto", "thread_id": ""},
    {"kind": "preference", "content": "偏好简洁结论先行的回答风格", "source": "explicit", "thread_id": ""},
]


# ============================================================
# Store 连接生命周期
# ============================================================

def open_store():
    """短命 AsyncSqliteStore 上下文（每次读写在独立连接内完成，随用随关）。

    用法: async with open_store() as store: ...
    """
    from langgraph.store.sqlite.aio import AsyncSqliteStore

    return AsyncSqliteStore.from_conn_string(STORE_DB)


async def ensure_store_setup():
    """建表（首次启动调用一次，放 main.py startup，不放请求路径上）。"""
    async with open_store() as store:
        await store.setup()
    log.info("[Memory] Store 初始化完成")


# ============================================================
# 记忆抽取（规则优先）
# ============================================================

def extract_watch_stocks(query: str, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从查询文本 + 会话终态快照抽取 watch_stock 记忆。

    - 快照来源（研究完成时自动记录本次分析的股票）: pending_stock_code /
      financial_data.stock_code —— source=auto
    - 查询显式提及（"关注/记住 600196"）—— source=explicit
    """
    memories: List[Dict[str, Any]] = []

    # 研究产物中的股票代码（auto，确定性最高）
    auto_codes: List[str] = []
    if snapshot.get("pending_stock_code"):
        auto_codes.append(str(snapshot["pending_stock_code"]))
    fin = snapshot.get("financial_data") or {}
    if isinstance(fin, dict) and fin.get("stock_code"):
        auto_codes.append(str(fin["stock_code"]))

    for code in dict.fromkeys(auto_codes):  # 保序去重
        if _STOCK_CODE_RE.fullmatch(code):
            memories.append({
                "kind": "watch_stock",
                "content": f"用户研究过股票 {code}",
                "stock_code": code,
                "source": "auto",
                "thread_id": "",
            })

    # 查询中显式表达的关注意图（explicit）
    if _WATCH_KEYWORD_RE.search(query or ""):
        for m in _STOCK_CODE_RE.finditer(query):
            code = m.group(1)
            if not any(x["stock_code"] == code for x in memories):
                memories.append({
                    "kind": "watch_stock",
                    "content": f"用户长期关注股票 {code}",
                    "stock_code": code,
                    "source": "explicit",
                    "thread_id": "",
                })

    return memories


async def extract_explicit_memory(query: str) -> Optional[Dict[str, Any]]:
    """LLM 兜底：用户显式说"记住…"但不含股票代码时，轻量调用抽取结构化记忆。

    失败静默返回 None（fail-open），绝不阻塞主流程。
    """
    if not _REMEMBER_KEYWORD_RE.search(query or ""):
        return None
    # 已由规则覆盖的股票记忆场景不再走 LLM
    if _STOCK_CODE_RE.search(query or ""):
        return None

    import json as _json
    from app.utils.llm import llm_invoke
    from langchain_core.messages import HumanMessage

    prompt = (
        '从下面这句话中抽取一条值得长期记住的用户信息。\n'
        f'句子：{query}\n'
        '只返回 JSON（不要其他文字）：{"kind": "preference|fact", "content": "<一句话>"}\n'
        '如果这句话没有可长期记住的信息，返回 {"kind": "none", "content": ""}'
    )
    try:
        resp = await asyncio.to_thread(llm_invoke, [HumanMessage(content=prompt)], node="memory_extract")
        data = _json.loads(resp.content.strip().strip('`').removeprefix('json').strip())
        kind, content = data.get("kind"), (data.get("content") or "").strip()
        if kind in ("preference", "fact") and content:
            return {"kind": kind, "content": content, "source": "explicit", "thread_id": ""}
    except Exception as e:
        log.warning(f"[Memory] LLM 抽取失败（忽略）: {e}")
    return None


# ============================================================
# 读写
# ============================================================


async def save_memories(user_id: str, memories: List[Dict[str, Any]], thread_id: str = "") -> int:
    """批量写入并执行容量淘汰。独立短命 store 上下文，供后台任务调用。"""
    if not memories or not user_id:
        return 0
    written = 0
    try:
        async with open_store() as store:
            for mem in memories:
                if await save_memory_into(store, user_id, mem, thread_id):
                    written += 1
            await evict_oldest(store, user_id)
    except Exception as e:
        log.warning(f"[Memory] 批量写入失败（忽略）: {e}")
    return written


async def save_memory_into(store, user_id: str, memory: Dict[str, Any], thread_id: str = "") -> Optional[str]:
    """save_memory 的显式 store 版本（同一上下文内多次写入复用连接）。"""
    kind = memory.get("kind", "fact")
    if kind == "watch_stock" and memory.get("stock_code"):
        key = f"watch:{memory['stock_code']}"
    else:
        key = uuid.uuid4().hex
    try:
        await store.aput((MEMORY_NAMESPACE_PREFIX, user_id), key, {**memory, "thread_id": thread_id})
        return key
    except Exception as e:
        log.warning(f"[Memory] 写入失败（忽略）: {e}")
        return None


async def evict_oldest(store, user_id: str):
    """每用户上限 MAX_MEMORIES_PER_USER，超出淘汰最旧（updated_at 升序删）。"""
    items = await store.asearch((MEMORY_NAMESPACE_PREFIX, user_id), limit=10_000)
    overflow = len(items) - MAX_MEMORIES_PER_USER
    if overflow <= 0:
        return
    ordered = sorted(items, key=lambda it: getattr(it, "updated_at", "") or "")
    for it in ordered[:overflow]:
        try:
            await store.adelete((MEMORY_NAMESPACE_PREFIX, user_id), it.key)
        except Exception as e:
            log.warning(f"[Memory] 淘汰最旧记忆失败（忽略）: {e}")
    log.info(f"[Memory] 用户 {user_id} 超容，淘汰最旧 {overflow} 条")


async def load_user_memories(store, user_id: str, limit: int = LOAD_LIMIT) -> List[str]:
    """读取用户记忆内容列表（注入 prompt 用）。Store 不可用返回空表（fail-open）。"""
    if store is None or not user_id:
        return []
    try:
        items = await store.asearch((MEMORY_NAMESPACE_PREFIX, user_id), limit=limit)
        contents = []
        for it in items:
            v = it.value or {}
            if v.get("content"):
                contents.append(str(v["content"]))
        return contents
    except Exception as e:
        log.warning(f"[Memory] 读取失败（降级为无记忆）: {e}")
        return []


async def list_all_memories(user_id: str) -> List[Dict[str, Any]]:
    """管理 API：列出该用户全部记忆（含 key/metadata）。"""
    out: List[Dict[str, Any]] = []
    try:
        async with open_store() as store:
            items = await store.asearch((MEMORY_NAMESPACE_PREFIX, user_id), limit=10_000)
            for it in items:
                v = it.value or {}
                out.append({
                    "key": it.key,
                    "kind": v.get("kind", "fact"),
                    "content": v.get("content", ""),
                    "source": v.get("source", ""),
                    "updated_at": str(getattr(it, "updated_at", "") or ""),
                })
    except Exception as e:
        log.warning(f"[Memory] 列举失败: {e}")
    return out


async def delete_memory(user_id: str, key: str) -> bool:
    """管理 API：删除单条。红线操作由前端二次确认。"""
    try:
        async with open_store() as store:
            await store.adelete((MEMORY_NAMESPACE_PREFIX, user_id), key)
            return True
    except Exception as e:
        log.warning(f"[Memory] 删除失败: {e}")
        return False


# ============================================================
# 会话级入口（routes.py 后台任务调用）
# ============================================================

async def remember_from_session(user_id: str, query: str, snapshot: Dict[str, Any],
                                thread_id: str = "") -> None:
    """会话结束后的后台记忆写入：规则优先 + LLM 兜底，全链路不抛错。"""
    try:
        memories = extract_watch_stocks(query, snapshot)
        explicit = await extract_explicit_memory(query)
        if explicit:
            memories.append(explicit)
        if not memories:
            return
        n = await save_memories(user_id, memories, thread_id=thread_id)
        if n:
            log.info(f"[Memory] 会话结束写入 {n} 条记忆 (user={user_id})")
    except Exception as e:
        log.warning(f"[Memory] 后台记忆写入异常（忽略）: {e}")


async def seed_demo_memories():
    """启动时给默认用户预置演示记忆（已有记忆则跳过，幂等）。"""
    try:
        async with open_store() as store:
            existing = await store.asearch((MEMORY_NAMESPACE_PREFIX, DEMO_USER_ID), limit=1)
            if existing:
                return
            for mem in DEMO_MEMORIES:
                await save_memory_into(store, DEMO_USER_ID, mem)
            log.info(f"[Memory] 已预置 {len(DEMO_MEMORIES)} 条演示记忆 (user={DEMO_USER_ID})")
    except Exception as e:
        log.warning(f"[Memory] 演示记忆预置失败（不影响服务）: {e}")
