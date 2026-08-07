from langchain_core.messages import HumanMessage
from app.utils.llm import llm_invoke
from app.utils.streaming import llm_stream_tokens, get_token_queue
from app.utils.memory import build_conversation_context
from app.skills.router import get_skill_prompt, get_skill_memory_policy
from app.graph.state import AgentState
from app.utils.json_utils import parse_json_response
from app.utils.logger import get_logger
from app.memory.store import MemoryStore

log = get_logger("planner")

PLAN_PROMPT = """你是一个专业的研究规划师。请把用户的研究主题拆解为 3-5 个子任务，每个子任务给出 1-2 个独立的搜索子问题。

{conversation_context}

重要规则：
- 子任务之间要互相独立、覆盖主题的不同侧面（背景/现状/对比/影响/趋势等）
- 如果存在「已搜索方向」列表，**严禁重复**这些方向，必须从全新的角度切入
- 如果存在审查意见，请针对意见中提到的缺失信息生成搜索方向
- 每个搜索子问题要具体、可检索、能在搜索引擎中找到高质量结果

严格按以下 JSON 数组输出，不要 Markdown，不要解释：
[
  {{"subtask": "子任务描述", "queries": ["搜索子问题1", "搜索子问题2"]}},
  {{"subtask": "子任务描述", "queries": ["搜索子问题1"]}}
]
"""


async def plan_node(state: AgentState):
    log.info("正在规划搜索路径")

    # 读取 Semantic 记忆（用户偏好）注入 prompt
    memory_context = ""
    try:
        store = MemoryStore()
        prefs_records = store.search("", kind="semantic", limit=3)
        if prefs_records:
            prefs_text = "\n".join(f"- {r.content}" for r in prefs_records)
            memory_context = f"\n\n## 用户历史偏好\n{prefs_text}"
    except Exception as e:
        log.debug(f"读取 Semantic 记忆失败: {e}")

    # 组装对话上下文（含历史摘要、已搜方向避让、当前问题）
    conversation_context = build_conversation_context(state)

    # Skill Prompt 注入（从 state 读取，router 节点已写入 active_skill）
    skill_prompt = ""
    active_skill = state.get("active_skill", "")
    if active_skill:
        skill_prompt_text = get_skill_prompt(active_skill)
        if skill_prompt_text:
            skill_prompt = f"\n\n## 调研策略\n{skill_prompt_text}"
            log.info(f"注入 Skill Prompt: {active_skill}")

        # Skill 打通记忆：按 memory_policy 决定读取哪些记忆层
        policy = get_skill_memory_policy(active_skill)
        if "episodic" in policy:
            try:
                episodic = store.search(state.get("query", ""), kind="episodic", limit=3)
                if episodic:
                    ep_text = "\n".join(f"- {r.content[:200]}" for r in episodic)
                    memory_context += f"\n\n## 历史研究参考（避免重复调研）\n{ep_text}"
                    log.info(f"Skill '{active_skill}' 注入 Episodic 记忆 {len(episodic)} 条")
            except Exception as e:
                log.debug(f"读取 Episodic 记忆失败: {e}")

    prompt_text = PLAN_PROMPT.format(
        conversation_context=conversation_context + skill_prompt + memory_context,
    )

    if get_token_queue() is not None:
        response_text = await llm_stream_tokens(
            [HumanMessage(content=prompt_text)],
            model_type="fast",
            node_name="planner",
            node="planner",
        )
    else:
        response = llm_invoke([HumanMessage(content=prompt_text)], node="planner")
        response_text = response.content

    # 解析结构化计划，失败则回退到逗号分隔的拍平列表
    structure = _parse_plan(response_text)

    # 派生拍平搜索方向（向后兼容 extractor 等下游）
    flat_queries = []
    for item in structure:
        for q in item.get("queries", []):
            if isinstance(q, str) and q.strip() and q.strip() not in flat_queries:
                flat_queries.append(q.strip())

    if not flat_queries:
        log.warning("计划解析失败，使用用户原始问题作为唯一方向")
        structure = [{"subtask": state.get("query", ""), "queries": [state.get("query", "")]}]
        flat_queries = [state.get("query", "")]

    # 首次进入 planner（NEW_TOPIC）时清理旧报告状态
    # revision_number > 0 表示是审查失败后的重试，不清
    result = {"plan": flat_queries, "plan_structure": structure}
    if state.get("revision_number", 0) == 0:
        if state.get("final_report", "").strip():
            log.info("新主题：清理旧报告和引用，防止污染新主题的搜索方向")
            result["final_report"] = ""
            result["citation_refs"] = ""
    return result


def _parse_plan(text: str) -> list:
    parsed = parse_json_response(text)
    if isinstance(parsed, list):
        structure = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            subtask = str(item.get("subtask", "")).strip()
            raw_queries = item.get("queries", [])
            if isinstance(raw_queries, str):
                raw_queries = [raw_queries]
            queries = [str(q).strip() for q in raw_queries if isinstance(q, str) and q.strip()]
            if subtask and queries:
                structure.append({"subtask": subtask, "queries": queries})
        if structure:
            return structure

    # 回退：逗号分隔
    tokens = [p.strip() for p in text.split(",") if p.strip()]
    if tokens:
        return [{"subtask": tokens[0], "queries": [t for t in tokens if t]}]
    return []