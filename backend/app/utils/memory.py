"""
会话记忆管理：摘要 + 压缩
- conversation_summary: 运行摘要（通过 checkpoint 持久化）
- writer/refiner 每轮增量更新摘要
- 摘要记录：搜索方向 + 核心发现 + 用户关注点，供 planner 避免重复搜索
"""
from app.utils.llm import llm_invoke
from app.utils.logger import get_logger
from langchain_core.messages import HumanMessage

log = get_logger("memory")

# 摘要长度阈值（字符数）
SUMMARY_MAX_CHARS = 2000


def _truncate_at_sentence(text: str, max_chars: int) -> str:
    """
    按句子边界截断，避免在句子中间切断产生乱码。
    优先在句号、感叹号、问号处断开；找不到则在逗号处断开；实在没有则硬截。
    """
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    # 从末尾往前找句子终止符
    for sep in ["。", "！", "？", ".", "!", "?"]:
        pos = truncated.rfind(sep)
        if pos > max_chars * 0.3:  # 至少保留 30% 内容
            return truncated[: pos + 1]
    # 退而求其次，在逗号处断开
    pos = truncated.rfind("，")
    if pos > max_chars * 0.3:
        return truncated[: pos + 1]
    # 硬截断
    return truncated + "..."


def update_conversation_summary(
    old_summary: str,
    query: str,
    report: str,
    critique: str = "",
    search_directions: list[str] | None = None,
) -> str:
    """
    增量更新对话摘要。每轮由 writer 或 refiner 调用。

    摘要结构（供 planner 规划时参考）：
    - 搜索了什么方向
    - 发现了什么核心信息
    - 用户关注什么
    - 有什么审查意见待修正
    """
    # 构造本轮记录
    turn_parts = [f"用户: {query}"]

    if search_directions:
        directions_str = "、".join(search_directions)
        turn_parts.append(f"搜索方向: {directions_str}")

    # 报告核心内容：取前 300 字符，保留完整句子
    report_excerpt = _truncate_at_sentence(report[:500], 300) if report else ""
    if report_excerpt:
        turn_parts.append(f"报告要点: {report_excerpt}")

    if critique:
        critique_excerpt = _truncate_at_sentence(critique, 150)
        turn_parts.append(f"审查意见: {critique_excerpt}")

    turn_text = "\n".join(turn_parts)

    # 如果没有旧摘要，直接返回本轮
    if not old_summary:
        return turn_text

    # 如果摘要还没超阈值，追加
    new_text = f"{old_summary}\n\n{turn_text}"
    if len(new_text) <= SUMMARY_MAX_CHARS:
        return new_text

    # 超阈值：压缩旧摘要 + 保留本轮
    prompt = f"""将以下对话摘要压缩为 3-5 句简洁摘要。
保留: 调研方向、已搜索的关键主题、关键发现、用户偏好、重要决策、未完成的修改。
忽略: 客套话、重复内容、格式细节、具体数据。

当前摘要（需压缩）:
{old_summary}

最新一轮:
{turn_text}

输出压缩后的完整摘要（包含历史要点和最新内容）:"""

    try:
        compressed = llm_invoke(
            [HumanMessage(content=prompt)],
            model_type="fast"
        ).content.strip()
        log.info(f"记忆压缩: {len(old_summary)} → {len(compressed)} 字符")
        return compressed
    except Exception as e:
        log.warning(f"记忆压缩失败: {e}，降级截断")
        return _truncate_at_sentence(new_text, SUMMARY_MAX_CHARS)


def build_conversation_context(state: dict) -> str:
    """
    组装对话上下文，注入到 planner/writer 的 prompt 中。
    从摘要中提取已搜索方向，供 planner 显式避让。
    """
    import re
    parts = []

    summary = state.get("conversation_summary", "")
    if summary:
        parts.append(f"[对话历史]\n{summary}")

        # 提取已搜索方向，生成避让指令
        searched = re.findall(r"搜索方向: (.+)", summary)
        if searched:
            all_directions = []
            for line in searched:
                all_directions.extend([d.strip() for d in line.split("、") if d.strip()])
            if all_directions:
                dedup = list(dict.fromkeys(all_directions))  # 去重保序
                parts.append(f"[已搜索方向（请勿重复，请从新角度切入）]\n" + "\n".join(f"- {d}" for d in dedup))

    parts.append(f"[当前问题] {state.get('query', '')}")

    return "\n\n".join(parts)
