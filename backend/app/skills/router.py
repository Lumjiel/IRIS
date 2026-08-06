"""
Skill 路由 — 基于 SkillRegistry 的便捷入口。

在 router 节点中调用 route_skill()，返回匹配的 skill name（或空字符串）。
"""
from app.config import SKILLS_ROOT
from app.skills.registry import SkillRegistry
from app.utils.logger import get_logger

log = get_logger("skill_router")

# 模块级单例，启动时加载一次
_registry: SkillRegistry | None = None


def _get_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry(SKILLS_ROOT)
    return _registry


def route_skill(query: str) -> str:
    """匹配用户查询对应的 Skill，返回 skill name 或空字符串。"""
    registry = _get_registry()
    return registry.match_skill(query) or ""


def get_skill_prompt(skill_name: str) -> str:
    """获取指定 Skill 的 prompt 模板。"""
    registry = _get_registry()
    return registry.get_active_skill_prompt(skill_name)
