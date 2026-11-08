"""
修订快速通道节点：审查未通过后的定向补搜。

背景（基线实测）：修订轮此前重跑完整研究管线（planner → researcher → 5 轮 FC 搜索 →
data_collector → writer），单轮 8-15 分钟且大头在与上一版几乎同题的网络搜索。
本节点只针对审查意见做一次定向 Tavily 搜索，结果追加进 messages 供修订撰写引用，
其余数据（行情/财务/上一版报告）复用 state 已有内容。
"""
from langchain_core.messages import HumanMessage

from app.graph.state import AgentState
from app.tools.search import search_tavily
from app.utils.logger import get_logger

log = get_logger("revision_search")


def revision_search_node(state: AgentState) -> dict:
    """按审查意见做一次定向搜索（fail-open：失败不阻塞修订，
    writer 会按诚实告知原则标注数据缺口）。"""
    critique = (state.get("critique") or "").strip()
    if not critique:
        return {}

    code = state.get("pending_stock_code") or ""
    query = f"{code} {critique[:150]}".strip() or critique
    try:
        result = search_tavily(query)
        content = result if isinstance(result, str) else str(result)
    except Exception as e:
        log.warning("[RevisionSearch] 定向补搜失败（fail-open）: %s", e)
        return {}

    log.info("[RevisionSearch] 定向补搜完成: query=%s", query[:80])
    return {
        "messages": [HumanMessage(content=f"[定向补搜·审查意见相关] {query}\n{content}")]
    }
