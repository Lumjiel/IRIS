"""
IRIS Router — 三意图路由
- RESEARCH : 新课题，启动完整研究 graph
- REFINE   : 对现有报告的修改/追问
- CHAT     : 通用问答，不调 graph（对话模式）
"""
from langchain_core.messages import HumanMessage
from app.graph.state import AgentState
from app.utils.llm import llm_invoke
from app.utils.logger import get_logger

log = get_logger("router")


def _looks_like_refine(q: str) -> bool:
    """兜底：关键词匹配修订意图。
    只放"明确修订指令"，避免闲聊词（然后呢/接着/继续）误判。
    模糊词交给 LLM 分类器判断。"""
    triggers = [
        # 明确修订指令
        "改", "润色", "优化", "重写", "调整", "删", "加",
        "补充", "扩写", "写详细", "更通俗", "更正式",
        "章", "段", "标题", "格式", "引用", "总结", "结论",
    ]
    return any(t in q.strip() for t in triggers)
def _looks_like_research(q: str) -> bool:
    """启发式：是否像研究请求（含股票代码、公司名、行业词等）"""
    q = q.strip()
    # 含 6 位数字（股票代码）
    import re
    if re.search(r'\b(\d{6})\b', q):
        return True
    # 研究类动词
    research_verbs = [
        "分析", "研究", "调研", "评估", "看看", "了解", "查一下",
        "怎么样", "如何", "怎样", "值得", "投资", "买入", "卖出",
        "对比", "比较", "排行", "排名", "推荐",
    ]
    return any(v in q for v in research_verbs)


def route_query(state: AgentState) -> str:
    """三意图路由：RESEARCH / REFINE / CHAT"""
    query = state["query"]
    has_report = bool(state.get("final_report", "").strip())

    log.info(f"意图识别: '{query}' (已有报告: {has_report})")

    # 无报告时：只有 RESEARCH 或 CHAT
    if not has_report:
        if _looks_like_research(query):
            return "planner"
        # 走 LLM 二次确认（防启发式误判）
        intent = _llm_classify(query, has_report=False)
        return "planner" if intent == "RESEARCH" else "chat"

    # 有报告时：RESEARCH / REFINE / CHAT 三分
    if _looks_like_refine(query):
        return "refiner"

    intent = _llm_classify(query, has_report=True)
    if intent == "REFINE":
        return "refiner"
    if intent == "RESEARCH":
        return "planner"
    return "chat"


def _llm_classify(query: str, has_report: bool) -> str:
    """LLM 意图分类，返回 RESEARCH / REFINE / CHAT"""
    context = "当前已有一份研究报告。" if has_report else "当前没有研究报告。"
    prompt = f"""
{context}
用户最新输入: "{query}"

判断用户意图，只输出一个词：
- "RESEARCH"：用户提出全新的研究课题（如分析某只股票、某行业），需要启动完整研究流程
- "REFINE"：用户想要讨论、评价、修改、补充现有报告，或对报告内容的追问
- "CHAT"：通用闲聊、非研究问题（如问天气、打招呼、问你是谁、一般知识问答）

规则：
- 含股票代码(6位数字)或"分析/研究/看看"等研究动词 → RESEARCH
- 对现有报告的追问、评价、修改 → REFINE
- 无法归类为以上两者 → CHAT
- 模糊短句默认 REFINE（有报告）或 CHAT（无报告）
"""
    try:
        result = llm_invoke([HumanMessage(content=prompt)], node="router").content.strip().upper()
        if result in ("RESEARCH", "REFINE", "CHAT"):
            return result
        log.warning(f"Router 非法输出: {result!r}")
    except Exception as e:
        log.error(f"Router LLM 失败: {e}")

    # 兜底
    if has_report:
        return "REFINE" if _looks_like_refine(query) else "CHAT"
    return "CHAT"