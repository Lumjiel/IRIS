"""情景推演流水线：因子拆解 → 历史类比 → 影响推演 → 概率合成。

- 3 次 LLM 调用 + 并行 Tavily 搜索（复用主链降级机制）
- 每阶段 fail-soft：单阶段失败不炸整体，缺失部分诚实标注
- 输出结构化 JSON，前端直接渲染
"""
import asyncio
import json
import re
from datetime import date

from langchain_core.messages import HumanMessage

from app.scenario import prompts
from app.tools.search import search_tavily, tavily
from app.utils.llm import llm_invoke
from app.utils.logger import get_logger

log = get_logger("scenario")


def _extract_json(text: str) -> dict | None:
    """从 LLM 回复中稳健提取 JSON 对象（容忍 markdown 代码块包裹）。"""
    if not text:
        return None
    text = re.sub(r"```(?:json)?", "", text).strip()
    # 找第一个 { 到最后一个 } 之间的内容
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        log.warning(f"JSON 解析失败: {e}")
        return None


async def _decompose(scenario: str) -> dict:
    """阶段一：因子拆解 + 搜索词生成。"""
    resp = await asyncio.to_thread(
        llm_invoke,
        [HumanMessage(content=prompts.DECOMPOSE_PROMPT.format(scenario=scenario))],
        model_type="fast",
        node="planner",
    )
    data = _extract_json(resp.content) or {}
    factors = data.get("factors") or []
    queries = data.get("search_queries") or []
    if not factors:
        # 兜底：把原始情景当作单因子
        factors = [{"name": scenario[:30], "description": scenario,
                    "beneficiaries": [], "losers": []}]
    return {"factors": factors[:5], "queries": [q for q in queries if q][:6]}


async def _search_one(query: str) -> str:
    """单条 Tavily 搜索，fail-soft 返回空串。"""
    try:
        return (await asyncio.to_thread(search_tavily, query)) or ""
    except Exception as e:
        log.warning(f"搜索失败[{query}]: {e}")
        return ""


async def _gather_and_extract(scenario: str, queries: list[str]) -> dict:
    """阶段二：并行搜索 + 历史案例提取。搜索全挂时回退到 LLM 内置知识。"""
    if tavily and queries:
        results = await asyncio.gather(*[_search_one(q) for q in queries])
        search_context = "\n\n".join(
            f"【搜索词: {q}】\n{r}" for q, r in zip(queries, results) if r
        )
    else:
        search_context = ""
    if not search_context:
        search_context = "（联网搜索不可用，以下基于模型知识）"
    else:
        search_context = search_context[:8000]  # 控制上下文长度

    resp = await asyncio.to_thread(
        llm_invoke,
        [HumanMessage(content=prompts.ANALOGY_PROMPT.format(
            scenario=scenario, search_context=search_context))],
        model_type="fast",
        node="researcher",
    )
    data = _extract_json(resp.content) or {}
    cases = data.get("cases") or []
    used_web = bool(search_context) and search_context != "（联网搜索不可用，以下基于模型知识）"
    return {"cases": cases[:6], "used_web": used_web}


async def _synthesize(scenario: str, factors: list, cases: list) -> dict:
    """阶段三：因子叠加推演 + 概率合成（用 smart 档，温度 0）。"""
    resp = await asyncio.to_thread(
        llm_invoke,
        [HumanMessage(content=prompts.SYNTHESIZE_PROMPT.format(
            today=date.today().strftime("%Y-%m-%d"),
            scenario=scenario,
            factors=json.dumps(factors, ensure_ascii=False, indent=2),
            analogies=json.dumps(cases, ensure_ascii=False, indent=2),
        ))],
        model_type="smart",
        node="reviewer",
    )
    data = _extract_json(resp.content) or {}
    impacts = data.get("impacts") or []
    # 清洗概率：钳制到 50-95，direction 规范化
    for imp in impacts:
        try:
            p = int(float(imp.get("probability", 60)))
        except (TypeError, ValueError):
            p = 60
        imp["probability"] = max(50, min(95, p))
        imp["direction"] = "up" if str(imp.get("direction", "up")).lower().startswith("u") else "down"
    impacts.sort(key=lambda x: -abs(x["probability"] - 50))
    return {
        "summary": data.get("summary", "推演结论生成失败，以下仅为因子与案例供参考。"),
        "impacts": impacts,
        "confidence_note": data.get("confidence_note", ""),
    }


async def run_scenario_analysis(scenario: str) -> dict:
    """完整流水线入口。任何阶段异常都 fail-soft，保证返回结构完整。"""
    scenario = (scenario or "").strip()
    if not scenario:
        return {"ok": False, "error": "情景描述不能为空"}

    result = {
        "ok": True,
        "scenario": scenario,
        "factors": [],
        "cases": [],
        "used_web": False,
        "summary": "",
        "impacts": [],
        "confidence_note": "",
        "degraded": [],
    }

    # 阶段一：因子拆解
    try:
        dec = await _decompose(scenario)
        result["factors"] = dec["factors"]
        queries = dec["queries"]
    except Exception as e:
        log.error(f"因子拆解失败: {e}")
        result["degraded"].append("因子拆解失败，使用原始情景")
        result["factors"] = [{"name": scenario[:30], "description": scenario,
                              "beneficiaries": [], "losers": []}]
        queries = [f"{scenario[:40]} 历史类似事件 A股 板块 表现"]

    # 阶段二：历史类比
    try:
        ana = await _gather_and_extract(scenario, queries)
        result["cases"] = ana["cases"]
        result["used_web"] = ana["used_web"]
        if not ana["used_web"]:
            result["degraded"].append("联网搜索不可用，历史案例来自模型知识")
    except Exception as e:
        log.error(f"历史类比失败: {e}")
        result["degraded"].append("历史案例提取失败")
        result["cases"] = []

    # 阶段三：合成
    try:
        syn = await _synthesize(scenario, result["factors"], result["cases"])
        result.update({k: syn[k] for k in ("summary", "impacts", "confidence_note")})
    except Exception as e:
        log.error(f"推演合成失败: {e}")
        result["degraded"].append("推演合成失败")
        result["ok"] = False
        result["error"] = f"推演合成失败: {e}"

    result["disclaimer"] = prompts.DISCLAIMER
    return result
