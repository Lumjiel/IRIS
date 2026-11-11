"""memory.py 单测：摘要截断 / 增量更新 / 压缩降级 / 上下文组装。"""
from unittest.mock import patch, MagicMock

from langchain_core.messages import AIMessage

from app.utils.memory import (
    SUMMARY_MAX_CHARS,
    _truncate_at_sentence,
    build_conversation_context,
    update_conversation_summary,
)


class TestTruncateAtSentence:
    def test_short_text_untouched(self):
        assert _truncate_at_sentence("短文本", 100) == "短文本"

    def test_cut_at_period(self):
        text = "第一句。" + "x" * 50 + "第二句。" + "y" * 50
        out = _truncate_at_sentence(text, 60)
        assert out.endswith("。")
        assert len(out) <= 60

    def test_cut_at_comma_when_no_period(self):
        text = "a" * 40 + "，" + "b" * 40
        out = _truncate_at_sentence(text, 60)
        assert out.endswith("，")

    def test_hard_truncate_when_no_separator(self):
        text = "a" * 100
        out = _truncate_at_sentence(text, 60)
        assert out == "a" * 60 + "..."

    def test_separator_too_early_falls_back(self):
        # 句号出现在前 30% 内 → 不在该处断开，退到逗号/硬截
        text = "。" + "b" * 100
        out = _truncate_at_sentence(text, 60)
        assert len(out) <= 63


class TestUpdateConversationSummary:
    def test_first_turn_no_old_summary(self):
        out = update_conversation_summary("", "查茅台", "报告内容", search_directions=["基本面"])
        assert "用户: 查茅台" in out
        assert "搜索方向: 基本面" in out
        assert "报告要点: 报告内容" in out

    def test_append_within_threshold(self):
        out = update_conversation_summary("旧摘要", "新问题", "新报告")
        assert out.startswith("旧摘要")
        assert "用户: 新问题" in out

    def test_report_excerpt_empty_when_no_report(self):
        out = update_conversation_summary("", "q", "")
        assert "报告要点" not in out

    def test_critique_included_and_truncated(self):
        out = update_conversation_summary("", "q", "报告", critique="意" * 500)
        assert "审查意见" in out
        # 150 字截断
        assert len(out) < 500

    @patch("app.utils.memory.llm_invoke")
    def test_compress_over_threshold(self, mock_inv):
        mock_inv.return_value = AIMessage(content="压缩后的摘要")
        old = "旧" * SUMMARY_MAX_CHARS  # 超阈值
        out = update_conversation_summary(old, "新问题", "新报告")
        assert out == "压缩后的摘要"
        assert mock_inv.called
        # 压缩用 fast 模型
        assert mock_inv.call_args.kwargs.get("model_type") == "fast"

    @patch("app.utils.memory.llm_invoke")
    def test_compress_failure_falls_back_to_truncate(self, mock_inv):
        mock_inv.side_effect = RuntimeError("llm down")
        old = "旧" * SUMMARY_MAX_CHARS
        out = update_conversation_summary(old, "新问题", "新报告")
        # 降级：按句子边界截断到阈值内（硬截带省略号；旧摘要在前，新内容被截掉）
        assert len(out) == SUMMARY_MAX_CHARS + 3
        assert out.endswith("...")


class TestBuildConversationContext:
    def test_empty_state(self):
        out = build_conversation_context({"query": "当前问题"})
        assert out == "[当前问题] 当前问题"

    def test_with_summary(self):
        state = {"query": "q", "conversation_summary": "历史摘要"}
        out = build_conversation_context(state)
        assert "[对话历史]" in out
        assert "历史摘要" in out
        assert "[当前问题] q" in out

    def test_directions_extraction_and_dedup(self):
        summary = "搜索方向: 基本面、估值\n搜索方向: 基本面、行业"
        out = build_conversation_context({"query": "q", "conversation_summary": summary})
        assert "[已搜索方向" in out
        assert "- 基本面" in out
        assert "- 行业" in out
        # 去重保序：基本面只出现一次
        assert out.count("- 基本面") == 1

    def test_no_directions_no_avoidance_block(self):
        summary = "只有普通内容"
        out = build_conversation_context({"query": "q", "conversation_summary": summary})
        assert "[已搜索方向" not in out

    def test_blank_directions_skipped(self):
        summary = "搜索方向: 、、"
        out = build_conversation_context({"query": "q", "conversation_summary": summary})
        assert "[已搜索方向" not in out
