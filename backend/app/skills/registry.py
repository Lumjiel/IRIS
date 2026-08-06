"""
SkillRegistry — 扫描 builtin/ 和 data/skills/ 目录下的 SKILL.md，
提供 Skill 匹配、注册、注销、重载。

无需 pyyaml，用标准库解析 YAML frontmatter。
"""
import re
import shutil
from pathlib import Path
from typing import Optional, List

from app.skills.models import Skill
from app.utils.logger import get_logger

log = get_logger("skill_registry")

SKILL_FILE_NAME = "SKILL.md"


def _parse_skill_md(skill_dir: Path, is_builtin: bool = False) -> Optional[Skill]:
    """解析 SKILL.md：YAML frontmatter + Markdown prompt 模板。"""
    filepath = skill_dir / SKILL_FILE_NAME
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        log.warning(f"读取 SKILL.md 失败: {filepath} — {e}")
        return None

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if not match:
        log.warning(f"SKILL.md 缺少 YAML frontmatter: {filepath}")
        return None

    frontmatter_str, prompt_template = match.group(1), match.group(2)

    meta: dict = {}
    for line in frontmatter_str.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            value = [v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()]
        meta[key] = value

    name = meta.get("name", "")
    if not name:
        log.warning(f"SKILL.md 缺少 name 字段: {filepath}")
        return None

    return Skill(
        name=name,
        description=meta.get("description", ""),
        prompt_template=prompt_template.strip(),
        required_tools=meta.get("tools", []) if isinstance(meta.get("tools"), list) else [],
        memory_policy=meta.get("memory_policy", "none"),
        skill_dir=skill_dir,
        is_builtin=is_builtin,
    )


def _write_skill_md(skill: Skill) -> None:
    """将 Skill 序列化为 SKILL.md 文件。"""
    filepath = skill.skill_dir / SKILL_FILE_NAME
    skill.skill_dir.mkdir(parents=True, exist_ok=True)

    tools_str = ", ".join(skill.required_tools) if skill.required_tools else ""
    frontmatter = f"""---
name: {skill.name}
description: {skill.description}
tools: [{tools_str}]
memory_policy: {skill.memory_policy}
---"""

    content = f"{frontmatter}\n\n{skill.prompt_template}\n"
    filepath.write_text(content, encoding="utf-8")


class SkillRegistry:
    """扫描 builtin/ 和 data/skills/ 目录，管理所有已注册的 Skill。"""

    def __init__(self, builtin_dir: str, user_dir: str):
        self.builtin_dir = Path(builtin_dir)
        self.user_dir = Path(user_dir)
        self._skills: dict[str, Skill] = {}
        self.reload()

    def reload(self) -> None:
        """重新扫描所有 Skill 目录，清空并重建缓存。"""
        self._skills.clear()
        self._scan_dir(self.builtin_dir, is_builtin=True)
        self._scan_dir(self.user_dir, is_builtin=False)
        log.info(f"SkillRegistry 重载完成，共 {len(self._skills)} 个 Skill")

    def _scan_dir(self, directory: Path, is_builtin: bool) -> None:
        """递归扫描指定目录下的所有 SKILL.md。"""
        if not directory.is_dir():
            return
        for skill_dir in sorted(directory.iterdir()):
            if not skill_dir.is_dir():
                continue
            if any(part.startswith(".") for part in skill_dir.parts):
                continue
            skill_file = skill_dir / SKILL_FILE_NAME
            if skill_file.exists():
                skill = _parse_skill_md(skill_dir, is_builtin=is_builtin)
                if skill:
                    if skill.name in self._skills:
                        log.warning(f"Skill 名称冲突: {skill.name}，后加载的覆盖先加载的")
                    self._skills[skill.name] = skill
                    log.info(f"已注册 Skill: {skill.name} ({'builtin' if is_builtin else 'user'})")

    def scan_all(self) -> List[Skill]:
        """返回所有已注册 Skill 的列表。"""
        return list(self._skills.values())

    def get(self, name: str) -> Optional[Skill]:
        """按名称查找 Skill。"""
        return self._skills.get(name)

    def list_all(self) -> List[Skill]:
        """列出所有 Skill。"""
        return list(self._skills.values())

    def match_skill(self, query: str) -> Optional[str]:
        """根据用户查询匹配最相关的 Skill，返回 skill name 或 None。

        匹配策略：
        1. description 关键词命中（简单子串匹配）
        2. name 关键词命中
        未匹配到返回 None，系统行为与不加 Skill 时一致。
        """
        query_lower = query.lower()
        best_name = None
        best_score = 0

        def _bigrams(text: str) -> set:
            return {text[i:i+2] for i in range(len(text) - 1)}

        query_bigrams = _bigrams(query_lower)

        for name, skill in self._skills.items():
            score = 0
            desc_lower = skill.description.lower()
            desc_tokens = re.split(r"[\s,，、。/]+", desc_lower)
            for token in desc_tokens:
                if token and token in query_lower:
                    score += 2

            if len(desc_lower) >= 2:
                desc_bigrams = _bigrams(desc_lower)
                score += len(desc_bigrams & query_bigrams)

            name_tokens = name.lower().replace("_", " ").split()
            for token in name_tokens:
                if len(token) >= 2 and token in query_lower:
                    score += 1

            if score > best_score:
                best_score = score
                best_name = name

        if best_name and best_score >= 2:
            log.info(f"Skill 匹配: '{query}' → {best_name} (score={best_score})")
            return best_name

        log.debug(f"Skill 匹配失败: '{query}'，使用默认策略")
        return None

    def get_active_skill_prompt(self, skill_name: str) -> str:
        """返回 Skill 的 prompt_template 注入文本，未找到返回空字符串。"""
        skill = self._skills.get(skill_name)
        if skill:
            return skill.prompt_template
        return ""

    def register(self, skill: Skill) -> bool:
        """注册新 Skill（写入 data/skills/{name}/SKILL.md）。"""
        if skill.name in self._skills and self._skills[skill.name].is_builtin:
            log.error(f"无法注册: {skill.name} 是内置 Skill")
            return False
        skill.skill_dir = self.user_dir / skill.name
        _write_skill_md(skill)
        skill.is_builtin = False
        self._skills[skill.name] = skill
        log.info(f"已注册新 Skill: {skill.name}")
        return True

    def unregister(self, name: str) -> bool:
        """注销 Skill（删除目录，内置 Skill 拒绝删除）。"""
        skill = self._skills.get(name)
        if skill is None:
            log.warning(f"注销失败: Skill '{name}' 不存在")
            return False
        if skill.is_builtin:
            log.error(f"无法删除内置 Skill: {name}")
            return False
        if skill.skill_dir.exists():
            shutil.rmtree(skill.skill_dir)
        del self._skills[name]
        log.info(f"已注销 Skill: {name}")
        return True
