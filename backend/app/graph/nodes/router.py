"""
意图识别节点（教科书式重构）。

相比旧实现（entry 函数内联分类 + 模块级 _skill_cache 传参），本实现：
1. 把 router 变成真正的 LangGraph 节点，分类结果（intent/confidence/entities/active_skill）写回 state，
   不再用模块级缓存 hack，也修掉了「intent 从未真正进入 state」的隐患。
2. 结构化输出：LLM 返回 {intent, confidence, is_followup, entities, skill}，带置信度。
3. 新增 CLARIFY 意图：低置信度/语义含糊时反问澄清，而不是默认塞给 RESEARCH。
4. follow-up 识别：注入对话摘要 + 是否有报告，让 LLM 判断是否续聊并继承上一意图。
5. skill 参与路由：意图为 research 时，由 LLM 根据各 skill 的 description 选 skill（agent-squad 风格），
   匹配失败再回退到 bigram 匹配器。
"""
from dataclasses import dataclass, field
from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.state import AgentState
from app.utils.llm import llm_invoke
from app.utils.json_utils import parse_json_response
from app.utils.logger import get_logger
from app.skills.router import route_skill

log = get_logger("router")

VALID_INTENTS = {"research", "chat", "sql", "tool_call", "refine", "clarify"}

ROUTER_SYSTEM_PROMPT = """\
你是一个严谨的意图分类器。根据用户输入、对话摘要和可用 Skill，输出结构化 JSON。

可选意图（intent）：
- research: 需要深度调研/写作的报告任务，如"帮我调研XXX"、"分析XXX发展趋势"、"写报告"
- chat: 闲聊、问候、简单问答，如"你好"、"你是谁"、"谢谢"
- sql: SQL/数据库操作，如"帮我写个查询"、"查用户表"
- tool_call: 需要调用外部工具的一次性请求，如"翻译这段话"、"查一下今天的新闻"
- refine: 对已有报告的修改/补充/讨论，如"把第三段改详细"、"继续"、"补充一下"
- clarify: 语义含糊、无法判断、或缺少完成任务所需信息，需要向用户澄清

严格按以下 JSON 输出，不要 Markdown，不要解释：
{
  "intent": "research|chat|sql|tool_call|refine|clarify",
  "confidence": 0.0-1.0,
  "is_followup": true/false,
  "entities": ["从输入中抽取的关键实体，可为空数组"],
  "skill": "匹配到的 skill 名称，无则空字符串"
}

判断规则：
1. 若【当前没有报告】且输入不是续聊，refine 无效，应选其他意图。
2. 若输入是短回复/代词/续聊（如"继续"、"然后呢"、"你觉得呢"、"是"、"1"）且已有对话，
   视为 is_followup，优先选 refine 或继承对话方向。
3. intent 为 research 时，从下方 <skills> 中选最匹配的 skill；无明显匹配则 skill 留空（用默认策略）。
4. 若输入含糊、无法归类、或既不像新任务也不像续聊，选 clarify 并给低置信度。
"""


@dataclass
class IntentResult:
    intent: str = "research"
    confidence: float = 0.0
    is_followup: bool = False
    entities: List[str] = field(default_factory=list)
    skill: str = ""


def _list_skills() -> List[dict]:
    """获取所有已注册 Skill 的 name+description，供 LLM 路由。"""
    try:
        from app.skills.registry import SkillRegistry
        from app.config import SKILLS_BUILTIN_DIR, SKILLS_USER_DIR

        registry = SkillRegistry(SKILLS_BUILTIN_DIR, SKILLS_USER_DIR)
        return [
            {"name": s.name, "description": s.description}
            for s in registry.scan_all()
        ]
    except Exception as e:
        log.debug(f"读取 Skill 列表失败: {e}")
        return []


def _build_skill_catalog(skills: List[dict]) -> str:
    if not skills:
        return "(无可用 skill)"
    return "\n".join(f"- {s['name']}: {s['description']}" for s in skills)


def looks_like_refine(q: str) -> bool:
    q = q.strip()
    triggers = [
        "改", "润色", "优化", "补充", "扩写", "写详细", "更通俗", "更正式",
        "重写", "调整", "删", "加", "第", "章", "段", "标题", "格式",
        "总结", "结论", "引用",
        "你觉得", "你认为", "怎么看", "然后呢", "接着", "继续",
        "还有呢", "再说说", "深入", "详细说", "具体说",
    ]
    return any(t in q for t in triggers)


def _looks_like_research(q: str) -> bool:
    q = q.strip()
    verbs = [
        "调研", "研究", "分析", "报告", "调查", "梳理", "盘点", "评估", "趋势", "对比", "综述",
        "介绍", "简述", "解释", "说说", "讲讲", "介绍一下", "什么是", "为什么", "概述",
        "总结", "科普", "了解", "谢绍", "看看",
    ]
    return any(kw in q for kw in verbs)


def _looks_like_chat(q: str) -> bool:
    q = q.strip()
    return any(kw in q for kw in ["你好", "您好", "谢谢", "你是谁", "hi", "hello", "在吗", "早上好", "晚上好"])


def _looks_like_skill_manage(q: str) -> bool:
    """是否在请求管理 Skill（创建/删除/列出）——这类应走 tool_call。"""
    q = q.strip().lower()
    skill_tokens = ["skill", "技能", "策略模板"]
    verbs = ["创建", "新建", "生成", "制作", "做个", "写一个", "删除", "移除", "列出", "查看", "管理", "建立", "加一个", "弄一个", "搞一个"]
    return any(s in q for s in skill_tokens) and any(v in q for v in verbs)


def _looks_vague(q: str) -> bool:
    """判断输入是否"空泛"（无具体主题，仅语气词/请求），这类才该 clarify。"""
    q = q.strip()
    if len(q) < 4:
        return True
    fillers = ["帮我看看", "你看一下", "帮我一下", "帮我做个", "帮我搞个", "帮我", "看看", "弄一下", "搞一下", "帮我看下"]
    return any(f in q for f in fillers) and not _looks_like_research(q)


def _llm_classify(query: str, has_report: bool, summary: str, skill_catalog: str) -> Optional[dict]:
    context_lines = [f"当前是否已有报告: {'是' if has_report else '否'}"]
    if has_report:
        context_lines.append("（已有报告，refine 有效）")
    else:
        context_lines.append("（无报告，refine 无效）")
    if summary:
        context_lines.append(f"对话摘要: {summary[:500]}")

    classify_prompt = f"""用户输入: "{query}"

{chr(10).join(context_lines)}

<skills>
{skill_catalog}
</skills>

请输出 JSON。"""
    try:
        result = llm_invoke(
            [SystemMessage(content=ROUTER_SYSTEM_PROMPT), HumanMessage(content=classify_prompt)],
            node="router",
        ).content
        parsed = parse_json_response(result)
        if isinstance(parsed, dict):
            return parsed
    except Exception as e:
        log.warning(f"LLM 分类失败: {e}，启用兜底规则")
    return None


def route_node(state: AgentState) -> dict:
    """意图识别节点：分类并写回 state。"""
    query = state["query"]
    has_report = bool(state.get("final_report", "").strip())
    summary = state.get("conversation_summary", "")

    log.info(f"正在分析意图: '{query}' (已有报告: {has_report})")

    skills = _list_skills()
    skill_catalog = _build_skill_catalog(skills)
    parsed = _llm_classify(query, has_report, summary, skill_catalog)

    result = IntentResult()
    if parsed:
        raw_intent = str(parsed.get("intent", "")).strip().lower()
        if raw_intent in VALID_INTENTS:
            result.intent = raw_intent
        result.confidence = float(parsed.get("confidence", 0.0) or 0.0)
        result.is_followup = bool(parsed.get("is_followup", False))
        result.entities = parsed.get("entities") or []
        # skill：仅 research 才需要 skill；PLP 校验 skill 存在性
        skill_name = str(parsed.get("skill", "") or "").strip()
        if skill_name and any(s["name"] == skill_name for s in skills):
            result.skill = skill_name

    # ---- 兜底与约束 ----
    # Skill 管理请求（创建/删除/列出）优先路由到 tool_call（有 create_skill/list_skills/delete_skill 工具）
    if _looks_like_skill_manage(query) and not (has_report and looks_like_refine(query)):
        result.intent = "tool_call"

    valid_behavior = result.intent in {"research", "chat", "sql", "tool_call", "refine"}

    if not valid_behavior:
        # LLM 明确说 clarify，或低置信度无明确信号 → 用规则兜底，避免误澄清
        if has_report and looks_like_refine(query):
            result.intent = "refine"
        elif _looks_like_chat(query):
            result.intent = "chat"
        elif _looks_like_research(query) or not _looks_vague(query):
            # 有话题动词，或非空泛请求 → 默认 research（生成报告）
            result.intent = "research"
        else:
            result.intent = "clarify"
    # 无报告强制排除 refine（防 LLM 无视规则）
    if not has_report and result.intent == "refine":
        result.intent = "research"

    # 用户在前端强制指定了 skill（state.active_skill 非空）→ 尊重用户，不自动匹配
    forced_skill = (state.get("active_skill") or "").strip()
    if forced_skill:
        result.skill = forced_skill
        log.info(f"使用用户强制指定的 Skill: {forced_skill}")
    elif result.intent == "research" and not result.skill:
        # skill 回退：LLM 没选到但 bigram 能匹配
        try:
            matched = route_skill(query)
            if matched:
                result.skill = matched
        except Exception as e:
            log.debug(f"bigram skill 回退失败: {e}")

    log.info(
        f"意图判定: {result.intent} (置信度={result.confidence:.2f}, "
        f"followup={result.is_followup}, skill={result.skill or '无'})"
    )

    return {
        "intent": result.intent,
        "intent_confidence": result.confidence,
        "is_followup": result.is_followup,
        "entities": result.entities,
        "active_skill": result.skill,
    }


def route_intent(state: AgentState) -> str:
    """根据 state['intent'] 路由到具体节点（router 节点之后的条件边）。"""
    intent = state.get("intent", "").lower()
    if intent not in {"research", "chat", "sql", "tool_call", "refine", "clarify"}:
        # 理论上不会走到这里：router 节点已约束 intent，这里兜底回 planner
        log.warning(f"未知意图 {intent!r}，兜底到 research")
        return "research"
    return intent