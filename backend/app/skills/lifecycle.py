"""
Skill 生命周期管理 — 封装 CRUD 操作，处理 SKILL.md 的读写。
"""
from pathlib import Path
from typing import Optional, List

from app.skills.models import Skill
from app.utils.logger import get_logger

log = get_logger("skill_lifecycle")

# 模块级引用，由 init_skills() 初始化
_registry = None


def init_skills(builtin_dir: str, user_dir: str):
    """初始化 Skill 系统，创建 registry 单例。"""
    global _registry
    from app.skills.registry import SkillRegistry
    Path(user_dir).mkdir(parents=True, exist_ok=True)
    _registry = SkillRegistry(builtin_dir, user_dir)
    log.info(f"Skill 生命周期管理已初始化: builtin={builtin_dir}, user={user_dir}")


def _get_registry():
    global _registry
    if _registry is None:
        from app.config import SKILLS_BUILTIN_DIR, SKILLS_USER_DIR
        init_skills(SKILLS_BUILTIN_DIR, SKILLS_USER_DIR)
    return _registry


def create_skill(
    name: str,
    description: str,
    prompt_template: str,
    tools: Optional[List[str]] = None,
    memory_policy: str = "none",
) -> Skill:
    """创建新 Skill 并持久化到 data/skills/。"""
    registry = _get_registry()

    if registry.get(name):
        raise ValueError(f"Skill '{name}' 已存在")

    skill = Skill(
        name=name,
        description=description,
        prompt_template=prompt_template,
        required_tools=tools or [],
        memory_policy=memory_policy,
        skill_dir=registry.user_dir / name,
        created_at=Skill.now_iso(),
        updated_at=Skill.now_iso(),
    )
    registry.register(skill)
    return skill


def update_skill(name: str, **kwargs) -> Optional[Skill]:
    """更新指定 Skill 的字段并写回 SKILL.md。"""
    registry = _get_registry()
    skill = registry.get(name)
    if skill is None:
        return None
    if skill.is_builtin:
        raise PermissionError(f"内置 Skill '{name}' 不可修改")

    updatable = {"description", "prompt_template", "required_tools", "memory_policy"}
    changed = False
    for key, value in kwargs.items():
        if key in updatable and hasattr(skill, key):
            setattr(skill, key, value)
            changed = True

    if changed:
        skill.updated_at = Skill.now_iso()
        from app.skills.registry import _write_skill_md
        _write_skill_md(skill)
        log.info(f"Skill '{name}' 已更新")

    return skill


def delete_skill(name: str) -> bool:
    """删除 Skill（内置 Skill 拒绝删除）。"""
    registry = _get_registry()
    skill = registry.get(name)
    if skill is None:
        return False
    if skill.is_builtin:
        raise PermissionError(f"内置 Skill '{name}' 不可删除")
    return registry.unregister(name)


def get_skill(name: str) -> Optional[Skill]:
    """从 registry 查找 Skill。"""
    return _get_registry().get(name)


def list_skills() -> List[Skill]:
    """返回所有 Skill。"""
    return _get_registry().list_all()


def reload_skills() -> int:
    """重新扫描所有 Skill 目录，返回加载数量。"""
    registry = _get_registry()
    if registry is None:
        return 0
    registry.reload()
    return len(registry.scan_all())
