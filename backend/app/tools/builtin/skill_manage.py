"""Skill 管理工具：让 agent 通过自然语言创建/列出/删除 Skill。

注册到 ToolRegistry 后，ReAct 工具循环（tool_call⇄tool_execute）就能在对话中调用它们，
例如用户说"帮我创建一个调研XX的skill" -> router 判 tool_call -> ReAct 选 create_skill -> 真创建。
"""
from langchain_core.messages import HumanMessage

from app.tools.registry import ToolRegistry
from app.utils.llm import llm_invoke
from app.utils.json_utils import parse_json_response
from app.utils.logger import get_logger

log = get_logger("skill_manage_tool")

_CREATE_PROMPT = """你是一个 Skill 定义提取器。根据用户的自然语言，创建一个调研 Skill 所需的字段，输出严格 JSON：
{{
  "name": "小写英文字母/数字/下划线，如 tech_review",
  "description": "一句话说明该 Skill 适用的调研场景",
  "prompt_template": "给使用该 Skill 的调研 agent 的策略指令（Markdown，包含搜索策略、输出要求、写作建议）",
  "tools": ["web_search", "doc_search"]
}}

规则：
- name 用英文，若用户没给则根据场景生成
- prompt_template 要具体可执行，不要空泛
- tools 从可用的里选：web_search / doc_search / citation_search

用户请求：{query}
只输出 JSON，不要 Markdown。"""

_DELETE_PROMPT = """从用户的请求中提取要删除的 Skill 名称，只输出名称本身，不要其他内容。
用户请求：{query}"""


@ToolRegistry.register(
    name="create_skill",
    description="创建一个新的 Skill（可复用的调研策略模板）。用户说'帮我创建一个XX的skill/新建/生成/制作一个调研XX的skill'时使用。",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "用户创建 skill 的完整自然语言请求（含 skill 名称、用途、调研策略）"}},
        "required": ["query"],
    },
)
def create_skill(query: str) -> str:
    """根据自然语言创建 Skill。"""
    try:
        res = llm_invoke(
            [HumanMessage(content=_CREATE_PROMPT.format(query=query))],
            node="tool_executor",
        )
        data = parse_json_response(res.content)
        if not isinstance(data, dict) or not data.get("name"):
            return "无法解析 Skill 定义。请提供：skill 名称、它用于什么调研场景、以及对应的调研策略。"
        name = str(data["name"]).strip()
        description = str(data.get("description", "")).strip()
        prompt_template = str(data.get("prompt_template", "")).strip()
        tools = data.get("tools") or []
        if not prompt_template:
            prompt_template = (
                f"你是一个{description or name}领域的专业调研助手。\n"
                "请针对用户的问题做深度调研，收集多来源信息，交叉验证后输出结构清晰的报告，并带引用标注。"
            )
        # 校验工具名是否存在，剔除无效的
        valid = [t for t in tools if ToolRegistry.get(t)]
        from app.skills.lifecycle import create_skill as _create
        skill = _create(name=name, description=description, prompt_template=prompt_template, tools=valid)
        log.info(f"agent 创建 Skill: {name}")
        return (
            f"✅ 已创建 Skill「{skill.name}」\n"
            f"描述：{skill.description}\n"
            f"工具：{', '.join(skill.required_tools) or '默认全部'}\n\n"
            f"现在可以说「用 {skill.name} skill 帮我调研 XX」来使用它。"
        )
    except ValueError as e:
        return f"创建失败：{e}"
    except Exception as e:
        log.error(f"create_skill 失败: {e}")
        return f"创建 Skill 失败: {e}"


@ToolRegistry.register(
    name="list_skills",
    description="列出当前所有可用的 Skill 及其用途。用户想查看/了解有哪些 skill 时使用。",
    parameters={"type": "object", "properties": {}},
)
def list_skills(query: str = "") -> str:
    """列出所有 Skill。"""
    try:
        from app.skills.lifecycle import list_skills as _list
        skills = _list()
        if not skills:
            return "当前没有已配置的 Skill。"
        lines = [f"- **{s.name}**（{'内置' if s.is_builtin else '自定义'}）：{s.description}" for s in skills]
        return "当前 Skill 列表：\n" + "\n".join(lines)
    except Exception as e:
        log.error(f"list_skills 失败: {e}")
        return f"获取 Skill 列表失败: {e}"


@ToolRegistry.register(
    name="delete_skill",
    description="删除一个自定义 Skill（内置 Skill 不可删除）。用户说'删除/移除/不要XX这个skill'时使用。",
    parameters={
        "type": "object",
        "properties": {"name": {"type": "string", "description": "要删除的 Skill 名称"}},
        "required": ["name"],
    },
)
def delete_skill(name: str) -> str:
    """删除 Skill。"""
    try:
        name = (name or "").strip()
        if not name:
            return "无法确定要删除的 Skill 名称，请明确说出 skill 名字。"
        from app.skills.lifecycle import delete_skill as _delete
        ok = _delete(name)
        if ok:
            return f"✅ 已删除 Skill「{name}」"
        return f"Skill「{name}」不存在或为内置 Skill，无法删除。"
    except PermissionError as e:
        return f"删除失败：{e}"
    except Exception as e:
        log.error(f"delete_skill 失败: {e}")
        return f"删除 Skill 失败: {e}"