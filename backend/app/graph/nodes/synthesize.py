"""
Synthesize 节点 — Orchestrator-Worker 模式的「结果汇总结」阶段。

Planner 拆解任务 -> Researcher 并行检索 -> 本节点把分散的检索结果按子任务汇总成
一份结构化发现摘要，供 Writer 直接引用，避免 Writer 面对海量原始片段无从下手。
"""
from langchain_core.messages import HumanMessage
from app.graph.state import AgentState
from app.utils.llm import llm_invoke
from app.utils.logger import get_logger

log = get_logger("synthesize")

SYNTHESIZE_PROMPT = """你是一个研究分析师，负责把多个子任务的检索结果汇总成结构化发现摘要。

用户问题：{query}

各子任务的检索结果如下：
{structured}

请为每个子任务提炼 2-4 条关键发现，做到：
- 去除重复信息，保留每个子任务最有价值的事实、数据、观点
- 保留关键来源出处（标题或域名），方便后续引用标注
- 客观中立，不编造原始结果里没有的信息

输出格式（Markdown，按子任务分组）：
## <子任务名>
- <关键发现1>（来源：<标题/域名>）
- <关键发现2>
"""


def _flatten_findings(findings: list) -> str:
    """把 research_findings 拍平成可读文本。"""
    if not findings:
        return "(无检索结果)"
    blocks = []
    for item in findings:
        subtask = item.get("subtask", "")
        items = item.get("items", [])
        if not items:
            continue
        lines = [f"### {subtask}"]
        for it in items:
            if it.get("title"):
                lines.append(f"- {it['title']}: {it.get('content', '')[:500]}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) if blocks else "(无检索结果)"


def synthesize_node(state: AgentState) -> dict:
    log.info("正在汇总检索结果")
    findings = state.get("research_findings") or []
    structured = _flatten_findings(findings)

    if not structured.strip():
        return {"synthesis": ""}

    prompt = SYNTHESIZE_PROMPT.format(
        query=state["query"],
        structured=structured,
    )
    try:
        response = llm_invoke([HumanMessage(content=prompt)], model_type="fast", node="synthesize")
        synthesis = (response.content or "").strip()
        log.info(f"汇总完成: {len(synthesis)} 字符")
        return {"synthesis": synthesis}
    except Exception as e:
        log.warning(f"汇总失败: {e}，writer 将直接使用原始检索结果")
        return {"synthesis": ""}