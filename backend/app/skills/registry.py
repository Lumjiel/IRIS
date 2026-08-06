"""
SkillRegistry — 扫描 skills/ 目录下的 SKILL.md，提供 Skill 匹配和 Prompt 注入。

无需 pyyaml，用标准库解析 YAML frontmatter。
"""
import os
import re
from typing import Optional, Dict, List, Any
from app.utils.logger import get_logger

log = get_logger("skill_registry")


class Skill:
    """单个 Skill 的数据对象。"""

    def __init__(self, name: str, description: str, tools: List[str],
                 memory_policy: str, prompt_template: str, filepath: str):
        self.name = name
        self.description = description
        self.tools = tools
        self.memory_policy = memory_policy
        self.prompt_template = prompt_template
        self.filepath = filepath

    def __repr__(self):
        return f"Skill(name={self.name!r})"


def _parse_skill_md(filepath: str) -> Optional[Skill]:
    """解析 SKILL.md：YAML frontmatter + Markdown prompt 模板。"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        log.warning(f"读取 SKILL.md 失败: {filepath} — {e}")
        return None

    # 提取 --- 包裹的 frontmatter
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if not match:
        log.warning(f"SKILL.md 缺少 YAML frontmatter: {filepath}")
        return None

    frontmatter_str, prompt_template = match.group(1), match.group(2)

    # 简易 YAML 解析（不依赖 pyyaml）
    meta: Dict[str, Any] = {}
    for line in frontmatter_str.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # 处理列表值: [a, b, c]
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
        tools=meta.get("tools", []) if isinstance(meta.get("tools"), list) else [],
        memory_policy=meta.get("memory_policy", ""),
        prompt_template=prompt_template.strip(),
        filepath=filepath,
    )


class SkillRegistry:
    """扫描 skills/ 目录，管理所有已注册的 Skill。"""

    def __init__(self, skills_dir: str):
        self.skills_dir = skills_dir
        self._skills: Dict[str, Skill] = {}
        self._load_skills()

    def _load_skills(self):
        """递归扫描 skills_dir 下的所有 SKILL.md。"""
        if not os.path.isdir(self.skills_dir):
            log.info(f"Skills 目录不存在: {self.skills_dir}")
            return

        for root, _dirs, files in os.walk(self.skills_dir):
            for fname in files:
                if fname == "SKILL.md":
                    filepath = os.path.join(root, fname)
                    skill = _parse_skill_md(filepath)
                    if skill:
                        self._skills[skill.name] = skill
                        log.info(f"已注册 Skill: {skill.name} ({filepath})")

    @property
    def skill_names(self) -> List[str]:
        return list(self._skills.keys())

    def get_skill(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

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

        for name, skill in self._skills.items():
            score = 0
            # description 关键词匹配
            desc_lower = skill.description.lower()
            # 中文关键词拆分：按常见分隔符拆
            desc_tokens = re.split(r"[\s,，、/]+", desc_lower)
            for token in desc_tokens:
                if token and token in query_lower:
                    score += 2

            # name 中的关键词匹配（下划线拆分）
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
