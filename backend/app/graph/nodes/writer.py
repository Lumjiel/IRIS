"""
报告撰写：Map-Reduce 分章并行版。

- write_node（协调者）：组装共享上下文，按章 Send 6 个 write_chapter 并行实例
- write_chapter：按章路由上下文（控成本：不重复注入全部资料），llm_invoke 非流式
- assemble_writer：按固定章节序汇编全文，一次性推入 token 队列（前端流式渲染），
  并更新对话摘要

对比串行版：撰写时长从「各章之和」（4-6 分钟）降为「最慢一章」（约 1.5-2 分钟）；
上下文按章过滤，避免 6 倍全文注入的 token 膨胀。
"""
import asyncio
import time as _time
from contextvars import ContextVar

from langchain_core.messages import HumanMessage
from langgraph.types import Command, Send
from langsmith import traceable

from app.utils.llm import llm_invoke
from app.utils.streaming import get_token_queue, emit_node_event, get_queues_by_thread
from app.utils.memory import update_conversation_summary, build_conversation_context
from app.graph.nodes.load_memories import build_memory_block
from app.graph.state import AgentState
from app.utils.logger import get_logger
from app.agents.prompts import (
    CHINESE_REPORT_SYSTEM_PROMPT,
    DISCLAIMER,
    build_financial_tables,
    build_data_source_tags,
)

log = get_logger("writer")

# 本轮撰写起始时间（ContextVar：并发请求隔离；assemble 用它算 writer 总耗时）
_write_start_cv: ContextVar[float] = ContextVar("write_start", default=0.0)

# 写作风格映射
STYLE_MODIFIERS = {
    "detailed": "请写一份结构清晰、有深度的调研报告，内容详尽全面。",
    "concise": "请写一份简洁精炼的调研报告，突出核心结论，避免冗余。",
    "formal": "请用正式的学术/商业文风撰写调研报告，用词严谨专业。",
    "casual": "请用通俗易懂的语言撰写调研报告，让非技术读者也能理解。",
}

LANGUAGE_MODIFIERS = {
    "zh": "使用 Markdown 格式，全文中文。",
    "en": "Use Markdown format. Write the entire report in English.",
}

# 章节定义：标题 + 写作要点 + 上下文路由（控成本：各章只注入所需资料）
CHAPTER_SPECS = [
    {
        "title": "一、核心结论与投资摘要",
        "brief": "提炼最关键的投资观点（3-5 条），用一两句话总结整体判断。",
        "ctx": ["financial", "search"],
    },
    {
        "title": "二、公司概况",
        "brief": "主营业务、行业定位、竞争优势；用表格展示关键信息（指标 | 数值 | 来源），并标注信息来源。",
        "ctx": ["financial"],
    },
    {
        "title": "三、财务分析",
        "brief": "营收趋势、盈利质量、偿债能力；关键财务指标同比/环比变化；数据不足的指标明确标注「⚠️ 数据不足，暂不评价」；严禁编造具体数值。",
        "ctx": ["financial"],
    },
    {
        "title": "四、行业观点与竞争格局",
        "brief": "行业趋势判断；公司行业地位评估；引用网络搜索结果中的行业数据。",
        "ctx": ["search"],
    },
    {
        "title": "五、风险提示",
        "brief": "按重要性排序列出 3-5 条核心风险；区分系统性风险与个股风险；数据不足的维度必须标注「数据不足，暂不评价」。",
        "ctx": ["financial", "search"],
    },
    {
        "title": "六、投资建议（仅供参考）",
        "brief": "综合前述维度给出投资建议，口径必须为「仅供参考」。",
        "ctx": ["financial"],
    },
]


def _build_shared_context(state: AgentState) -> dict:
    """组装一次共享资料，供各章按 ctx 路由取用。"""
    financial_data = state.get("financial_data", {})
    data_sources = state.get("data_sources", [])
    return {
        "query": state["query"],
        "financial": (
            f"### 结构化数据（已由系统自动提取，请直接使用，不得改写数值）\n"
            f"{build_financial_tables(financial_data) or '（无结构化金融数据）'}\n\n"
            f"### 数据来源\n{build_data_source_tags(data_sources) or '（无数据源标注）'}"
        ),
        "search": (
            "### 网络调研资料\n"
            + ("\n\n".join(state.get("search_results") or []) or "（无网络搜索结果）")
        ),
        "conversation_context": build_conversation_context(state),
        "memory_block": build_memory_block(state),
    }


@traceable(run_type="chain", name="writer")
async def write_node(state: AgentState, config=None):
    """协调者：组装上下文 → Send 6 章并行实例。"""
    t0 = _time.time()
    _write_start_cv.set(t0)
    emit_node_event("writer", "start")
    try:
        log.info("分章并行撰写启动（%d 章）", len(CHAPTER_SPECS))
        shared = _build_shared_context(state)
        critique = state.get("critique", "")
        prefs = state.get("preferences", {})
        style_instruction = STYLE_MODIFIERS.get(prefs.get("style", "detailed"), STYLE_MODIFIERS["detailed"])
        language_instruction = LANGUAGE_MODIFIERS.get(prefs.get("language", "zh"), LANGUAGE_MODIFIERS["zh"])
        critique_section = (
            f'\n【重要提示】上一版本报告未通过审查，意见如下："{critique}"\n'
            "请务必在本次撰写中修正上述问题。\n" if critique else ""
        )
        # LangGraph 1.0：节点内向并行节点分发必须经 Command(goto=[Send...])，
        # 裸 list[Send] 会被当作 state update 拒绝（InvalidUpdateError）
        thread_id = (config or {}).get("configurable", {}).get("thread_id", "")
        return Command(
            goto=[
                Send(
                    "write_chapter",
                    {
                        **shared,
                        "thread_id": thread_id,
                        "chapter": spec,
                        "style_instruction": style_instruction,
                        "language_instruction": language_instruction,
                        "critique_section": critique_section,
                        "started_at": t0,
                    },
                )
                for spec in CHAPTER_SPECS
            ]
        )
    except Exception:
        emit_node_event("writer", "failed")
        raise


async def write_chapter_node(payload: dict) -> dict:
    """单章撰写（Send 并行实例，非流式；完成即发 progress 事件给前端时间线）。"""
    chapter = payload["chapter"]
    ctx_blocks = [payload[k] for k in chapter["ctx"] if payload.get(k)]
    prompt_text = f"""{CHINESE_REPORT_SYSTEM_PROMPT}

## 任务：只撰写报告中的这一章
**{chapter['title']}**
写作要点：{chapter['brief']}

## 用户问题
{payload['query']}

## 可用资料（只基于这些，严禁编造）
{chr(10).join(ctx_blocks)}

### 用户长期背景
{payload.get('memory_block') or '（无）'}

### 对话上下文
{payload.get('conversation_context') or '（无）'}
{payload['critique_section']}
## 输出要求
- 直接输出本章正文，以 `## {chapter['title']}` 开头，不要输出其他章节
- 数据缺失的维度，标注「⚠️ 数据不足，暂不评价」
{payload['style_instruction']}
{payload['language_instruction']}
"""
    # 同步 llm_invoke 必须下放线程池：直接调用会阻塞事件循环，
    # 导致六章实际串行执行且 SSE 心跳/事件全部停摆（E2E 实测教训）
    try:
        response = await asyncio.to_thread(
            llm_invoke, [HumanMessage(content=prompt_text)], node="writer"
        )
        text = response.content or ""
    except Exception as e:
        # 章节级 fail-open：单章失败不炸整图，汇编节点用占位章节兜底
        log.warning("[Writer] 章节 %s 撰写失败（fail-open）: %s", chapter["title"], e)
        text = ""
    text = response.content or ""
    if not text.strip():
        text = f"## {chapter['title']}\n\n⚠️ 数据不足，暂不评价。"
    # langgraph 并行实例不继承请求 ContextVar，凭 thread_id 从注册表取队列
    _emit_via_registry(payload.get("thread_id", ""), "writer", "progress",
                       data={"chapter_done": chapter["title"]})
    log.info("章节完成: %s（%d 字）", chapter["title"], len(text))
    return {"report_sections": {chapter["title"]: text}}


@traceable(run_type="chain", name="assemble_writer")
def _emit_via_registry(thread_id: str, step: str, status: str, elapsed: float = 0.0, data: dict | None = None):
    """经注册表发节点事件（ContextVar 在并行实例中不可用时的兜底通道）。"""
    import time as _time
    if elapsed <= 0:
        elapsed = 0.0
    reg = get_queues_by_thread(thread_id)
    if reg is None:
        return
    payload = {"step": step, "status": status}
    if elapsed > 0:
        payload["elapsed"] = round(elapsed, 2)
    if data is not None:
        payload["data"] = data
    reg["node"].put_nowait(payload)


@traceable(run_type="chain", name="assemble_writer")
async def assemble_writer_node(state: AgentState, config=None):
    """按固定章节序汇编全文 → 一次性流入 token 队列（前端即时渲染）→ 更新摘要。"""
    sections = state.get("report_sections") or {}
    parts = []
    for spec in CHAPTER_SPECS:
        part = (sections.get(spec["title"]) or "").strip()
        parts.append(part if part else f"## {spec['title']}\n\n⚠️ 本章生成失败，数据不足，暂不评价。")
    report = "\n\n".join(parts)

    if "免责" not in report and "不构成" not in report:
        report += DISCLAIMER

    # 汇编全文即时推送前端（分块入队，SSE 平滑渲染）；
    # 注册表优先（并行编排下 ContextVar 不可靠），无则回退 ContextVar
    thread_id = (config or {}).get("configurable", {}).get("thread_id", "")
    reg = get_queues_by_thread(thread_id) if thread_id else None
    token_q = (reg or {}).get("token") or get_token_queue()
    if token_q is not None:
        for i in range(0, len(report), 2000):
            await token_q.put({"step": "writer_token", "data": {"token": report[i:i + 2000]}})
        await token_q.put({"step": "writer_token", "data": {"token": "", "final": True}})

    elapsed = _elapsed_since(state)
    if reg is not None:
        _emit_via_registry(thread_id, "writer", "done", elapsed=elapsed)
    else:
        emit_node_event("writer", "done", elapsed=elapsed)
    log.info("分章撰写汇编完成（%d 字）", len(report))

    new_summary = update_conversation_summary(
        old_summary=state.get("conversation_summary", ""),
        query=state["query"],
        report=report,
        critique=state.get("critique", ""),
        search_directions=state.get("plan", []),
    )
    return {"final_report": report, "conversation_summary": new_summary}


def _elapsed_since(state: AgentState) -> float:
    started = _write_start_cv.get()
    return _time.time() - started if started else 0.0
