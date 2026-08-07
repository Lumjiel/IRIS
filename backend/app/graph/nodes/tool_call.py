"""
ReAct 工具调用 - 决策节点。

参考成熟 agent 方案（ReAct 模式）：LLM 根据用户请求 + 之前的工具结果，
结构化地决定「调用哪个工具（带参数）」还是「直接给出最终回答」。
图内与 tool_execute 节点构成循环，直到出答案或达到最大迭代轮数。
"""
import json
from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.state import AgentState
from app.utils.llm import llm_invoke
from app.utils.json_utils import parse_json_response
from app.utils.logger import get_logger
from app.config import MAX_TOOL_ITERATIONS

log = get_logger("tool_call")

TOOL_CALL_SYSTEM_PROMPT = """\
你是一个会使用工具的智能体。根据用户请求和之前的工具执行结果，决定下一步动作。

可用工具：
{tools_schema}

判断规则：
1. 如果调用某个工具能获得回答所需的信息，选择动作 tool。
2. 如果已有足够信息（或工具结果已给出答案），选择动作 answer，直接给出最终回答。
3. 你只能调用上述列出的工具，不要虚构工具名。
4. 已达到最大迭代轮数时，必须基于已有信息给出 answer。

只输出一个 JSON 对象，不要 Markdown、不要解释：
- 调用工具：{{"action":"tool","tool":"<工具名>","arguments":{{"参数名":"参数值"}}}}
- 直接回答：{{"action":"answer","answer":"<最终回答>"}}
"""


def _resolve_tools(state: AgentState) -> List:
    """按 active_skill 的 required_tools 约束可用工具；否则用全部。"""
    from app.tools.registry import ToolRegistry
    active_skill = state.get("active_skill", "")
    if active_skill:
        from app.skills.router import get_skill
        skill = get_skill(active_skill)
        if skill and skill.required_tools:
            available = []
            for tname in skill.required_tools:
                t = ToolRegistry.get(tname)
                if t:
                    available.append(t)
                else:
                    log.warning(f"Skill '{active_skill}' 声明的工具 '{tname}' 未注册，已跳过")
            if available:
                return available
    return ToolRegistry.list_all()


def _build_tools_schema(tools: List) -> str:
    lines = []
    for t in tools:
        params = t.parameters or {}
        if params:
            props = ", ".join(f"{k}: {v.get('type', 'string')}" for k, v in params.get("properties", {}).items())
            param_str = f" 参数({props})" if props else ""
        else:
            param_str = ""
        lines.append(f"- {t.name}: {t.description}{param_str}")
    return "\n".join(lines) if lines else "(无可用工具)"


def _build_history(state: AgentState) -> str:
    tool_messages = state.get("tool_messages", [])
    if not tool_messages:
        return "(尚无工具调用)"
    return "\n".join(f"{m.get('role')}: {m.get('content', '')}" for m in tool_messages)


def tool_call_node(state: AgentState) -> dict:
    query = state["query"]
    iterations = state.get("tool_iterations", 0)
    tools = _resolve_tools(state)

    # 达最大迭代轮数：强制用已有信息直接回答
    force_answer = iterations >= MAX_TOOL_ITERATIONS
    if force_answer:
        log.warning(f"达最大工具迭代数 {MAX_TOOL_ITERATIONS}，基于已有信息直接回答")

    tools_schema = _build_tools_schema(tools)
    history = _build_history(state)

    prompt = f"""用户请求: "{query}"

<工具执行历史>
{history}
</工具执行历史>

{'【注意】已达到最大迭代轮数，请直接基于已有工具结果回答，不要再调用工具。' if force_answer else ''}

请输出 JSON。"""
    try:
        result = llm_invoke(
            [SystemMessage(content=TOOL_CALL_SYSTEM_PROMPT.format(tools_schema=tools_schema)),
             HumanMessage(content=prompt)],
            node="tool_call",
        ).content
        parsed = parse_json_response(result)
    except Exception as e:
        log.error(f"ReAct 决策失败: {e}")
        parsed = None

    action = parsed.get("action") if isinstance(parsed, dict) else None

    if action == "tool" and not force_answer:
        tool_name = str(parsed.get("tool", "")).strip()
        arguments = parsed.get("arguments") or {}
        if not isinstance(arguments, dict):
            arguments = {"query": str(arguments)}
        # 工具名兜底模糊匹配
        if tool_name not in {t.name for t in tools}:
            for t in tools:
                if tool_name.lower() in t.name.lower() or t.name.lower() in tool_name.lower():
                    tool_name = t.name
                    break
        if not tool_name or tool_name not in {t.name for t in tools}:
            return {
                "final_report": f"抱歉，没有可用工具能处理该请求。可用工具：{', '.join(t.name for t in tools) or '无'}",
                "tool_call_request": None,
            }
        log.info(f"[ReAct] 调用工具: {tool_name} args={json.dumps(arguments, ensure_ascii=False)}")
        return {
            "tool_call_request": {"tool": tool_name, "arguments": arguments},
            "tool_iterations": iterations + 1,
        }

    # answer 分支
    answer = parsed.get("answer") if isinstance(parsed, dict) else None
    if not answer or not str(answer).strip():
        answer = "我无法完成这个请求，因为信息不足或没有合适的工具。"
    log.info("[ReAct] 直接回答")
    return {
        "final_report": str(answer).strip(),
        "tool_call_request": None,
    }