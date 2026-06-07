from langchain_core.messages import HumanMessage
from app.graph.state import AgentState
from app.utils.llm import llm_invoke
from app.utils.logger import get_logger

log = get_logger("router")


def looks_like_refine(q: str) -> bool:
    """兜底策略：关键词匹配"""
    q = q.strip()
    refine_triggers = ["改", "润色", "优化", "补充", "扩写", "写详细", "更通俗", "更正式", "重写", "调整", "删", "加", "第", "章", "段", "标题", "格式", "总结", "结论", "引用"]
    return any(t in q for t in refine_triggers)

def route_query(state: AgentState):
    """判断用户输入是"新查询"还是"修改指令" """
    query = state["query"]
    has_report = bool(state.get("final_report", "").strip())

    log.info(f"正在分析意图: '{query}' (已有报告: {has_report})")

    if not has_report:
        return "planner"

    prompt = f"""
    当前系统已经生成了一份研究报告。
    用户的最新输入是: "{query}"。
    用户最近一次生成的报告片段是："{state['final_report'][:500]}"

    请判断用户的意图：
    1. "NEW_TOPIC": 用户想要开始一个全新的研究课题。
    2. "REFINE": 用户想要基于现有的报告进行修改、润色或补充。

    只输出 "NEW_TOPIC" 或 "REFINE"。
    """

    result = llm_invoke([HumanMessage(content=prompt)]).content.strip().upper()
    log.info(f"LLM 判定结果: {result}")

    if result == "REFINE":
        return "refiner"
    if result == "NEW_TOPIC":
        return "planner"
    log.warning(f"非法输出: {result!r}，启用兜底规则")
    return "refiner" if looks_like_refine(query) else "planner"