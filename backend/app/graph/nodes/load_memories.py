"""
load_memories — 图入口首节点：从长期记忆 Store 读取用户背景并注入 state。

关键设计（docs/DESIGN_rerank_and_memory.md 3.3）：
- 只注入不路由：记忆影响"怎么答"，不影响"走哪条边"
- 前缀扫描取最近 N 条，非语义检索（简单、可预期、零额外成本）
- fail-open：store 缺失/异常时返回空记忆，主流程不受影响
"""
from typing import Any, Dict, List, Mapping, Optional

from app.utils.logger import get_logger
from app.utils.memory_store import load_user_memories

log = get_logger("graph.load_memories")


def build_memory_block(state: Mapping[str, Any]) -> str:
    """把 user_memories 拼装为 prompt 用户背景段（有记忆才拼，空则不加）。"""
    memories: List[str] = list(state.get("user_memories") or [])
    if not memories:
        return ""
    lines = "\n".join(f"- {m}" for m in memories[:5])
    return f"\n【用户长期背景】\n{lines}\n"


async def load_memories_node(
    state: Mapping[str, Any],
    *,
    store: Optional[Any] = None,
) -> Dict[str, Any]:
    """START 后首节点：读取记忆 → 写入 state.user_memories。"""
    user_id = state.get("user_id", "") or "default"

    if store is None:
        # 图编译未注入 store（如部分测试环境）：降级为无记忆
        log.debug("[Memory] 未注入 store，跳过记忆加载")
        return {"user_memories": []}

    contents = await load_user_memories(store, user_id)
    if contents:
        log.info(f"[Memory] 已注入 {len(contents)} 条用户记忆 (user={user_id})")
    return {"user_memories": contents}
