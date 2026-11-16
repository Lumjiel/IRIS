"""懒人模式：今日热点 → 一键情景。

进页面零输入：拉取今日财经快讯，LLM 提炼成 4-6 条情景短句，
用户点一下直接推演。新闻链路挂掉时回退静态预设（诚实标注）。

30 分钟内存缓存：热点提炼是纯只读操作，同批新闻没必要反复调 LLM。
"""
import asyncio
import json
import time

from langchain_core.messages import HumanMessage

from app.scenario import prompts
from app.utils.llm import llm_invoke
from app.utils.logger import get_logger

log = get_logger("scenario_suggest")

_CACHE: dict = {"ts": 0.0, "data": None}
_TTL = 30 * 60  # 30 分钟


async def _fetch_news_titles(limit: int = 15) -> list[str]:
    """今日财经快讯标题（东财，fail-soft）。"""
    try:
        import akshare as ak
        df = await asyncio.to_thread(ak.stock_info_global_em)
        titles = []
        for _, row in df.head(30).iterrows():
            t = str(row.get("标题") or "").strip()
            if not t:
                t = str(row.get("摘要") or "").strip()[:50]
            if t:
                titles.append(t[:60])
            if len(titles) >= limit:
                break
        return titles
    except Exception as e:
        log.warning(f"热点快讯获取失败: {e}")
        return []


async def _llm_suggest(titles: list[str]) -> list[str]:
    """LLM 把快讯提炼成情景短句。"""
    resp = await asyncio.to_thread(
        llm_invoke,
        [HumanMessage(content=prompts.SUGGEST_PROMPT.format(
            titles="\n".join(f"- {t}" for t in titles)))],
        model_type="fast",
        node="planner",
    )
    text = resp.content or ""
    # 复用 pipeline 的 JSON 提取（容忍代码块包裹）
    from app.scenario.pipeline import _extract_json
    data = _extract_json(text) or {}
    out = [s.strip() for s in (data.get("suggestions") or []) if s and s.strip()]
    return [s[:30] for s in out][:6]


async def get_suggestions(force: bool = False) -> dict:
    """返回 {mode: "news"|"preset", suggestions: [...]}。fail-soft，永不抛异常。"""
    now = time.time()
    if not force and _CACHE["data"] and now - _CACHE["ts"] < _TTL:
        return _CACHE["data"]

    titles = await _fetch_news_titles()
    suggestions: list[str] = []
    mode = "preset"
    if len(titles) >= 3:
        try:
            suggestions = await _llm_suggest(titles)
            if suggestions:
                mode = "news"
        except Exception as e:
            log.warning(f"热点情景提炼失败: {e}")
    if not suggestions:
        suggestions = prompts.PRESET_SUGGESTIONS

    data = {"mode": mode, "suggestions": suggestions}
    _CACHE.update(ts=now, data=data)
    return data
