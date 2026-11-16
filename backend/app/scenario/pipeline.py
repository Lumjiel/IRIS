"""情景推演流水线：因子拆解 → 历史类比 → 影响推演 → 概率合成。

- 3 次 LLM 调用 + 并行 Tavily 搜索（复用主链降级机制）
- 每阶段 fail-soft：单阶段失败不炸整体，缺失部分诚实标注
- iter_scenario_events: 异步事件流（真实阶段进度，SSE 消费）
- run_scenario_analysis: 一次性收集（兼容旧调用方/测试）
- verify_run: 事后验证——推演日至今各标的实际涨跌 vs 预测方向
"""
import asyncio
import json
import re
from datetime import date

from langchain_core.messages import HumanMessage

from app.scenario import prompts, storage
from app.tools.search import search_tavily, tavily
from app.utils.llm import llm_invoke
from app.utils.logger import get_logger

log = get_logger("scenario")

STAGE_LABELS = {
    "decompose": "拆解风险因子",
    "analogy": "联网检索历史类比案例",
    "synthesize": "因子叠加推演与概率合成",
}


def _stage(key: str, status: str) -> dict:
    return {"type": "stage", "key": key, "label": STAGE_LABELS.get(key, key), "status": status}


def _extract_json(text: str) -> dict | None:
    """从 LLM 回复中稳健提取 JSON 对象（容忍 markdown 代码块包裹）。"""
    if not text:
        return None
    text = re.sub(r"```(?:json)?", "", text).strip()
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


async def iter_scenario_events(scenario: str):
    """事件流版流水线。yield 阶段进度事件，最后 yield 完整结果（含 run_id 自动存档）。

    事件格式：
      {"type": "stage", "key": ..., "label": ..., "status": "start"|"done"}
      {"type": "result", "data": {...}}   # 完整推演结果
      {"type": "error", "detail": ...}    # 情景为空等前置错误
    """
    scenario = (scenario or "").strip()
    if not scenario:
        yield {"type": "error", "detail": "情景描述不能为空"}
        return

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
        "created_at": datetime_now(),
    }
    queries = []

    # 阶段一：因子拆解
    yield _stage("decompose", "start")
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
    yield _stage("decompose", "done")

    # 阶段二：历史类比
    yield _stage("analogy", "start")
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
    yield _stage("analogy", "done")

    # 阶段三：合成
    yield _stage("synthesize", "start")
    try:
        syn = await _synthesize(scenario, result["factors"], result["cases"])
        result.update({k: syn[k] for k in ("summary", "impacts", "confidence_note")})
    except Exception as e:
        log.error(f"推演合成失败: {e}")
        result["degraded"].append("推演合成失败")
        result["ok"] = False
        result["error"] = f"推演合成失败: {e}"
    yield _stage("synthesize", "done")

    result["disclaimer"] = prompts.DISCLAIMER

    # 自动存档（fail-soft，不影响结果返回）
    run_id = storage.save_run(scenario, result)
    result["run_id"] = run_id
    if run_id:
        result["saved"] = True

    yield {"type": "result", "data": result}


def datetime_now() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def run_scenario_analysis(scenario: str) -> dict:
    """一次性收集版：消费事件流，返回最终结果（兼容旧调用方）。"""
    final = None
    async for ev in iter_scenario_events(scenario):
        if ev.get("type") == "result":
            final = ev["data"]
        elif ev.get("type") == "error":
            final = {"ok": False, "error": ev["detail"], "scenario": scenario}
    return final


# ============ 事后验证 ============

_CODE_RE = re.compile(r"\d{6}")


def _extract_code(target: str) -> str | None:
    """从推演目标中提取 6 位 A 股代码（如"黄金：山东黄金(600547)"）。"""
    m = _CODE_RE.search(target or "")
    return m.group(0) if m else None


async def _kline_since(code: str, start_date: str, max_days: int = 130) -> dict | None:
    """拉取覆盖 start_date 至今的日 K（全日期 + 收盘价）。

    复用 K 线三级降级源（东财→新浪→腾讯），返回全日期以便定位推演日基线。
    """
    prefix = "sh" if code.startswith("6") else "sz"
    ua = {"User-Agent": "Mozilla/5.0"}

    # 主源：东财（带全日期）
    for attempt in range(2):
        try:
            import akshare as ak
            df = await asyncio.to_thread(
                ak.stock_zh_a_hist, symbol=code, period="daily", adjust="qfq"
            )
            if df is not None and not df.empty:
                return {
                    "dates": [str(x)[:10] for x in df["日期"].astype(str).tolist()],
                    "closes": [round(float(x), 2) for x in df["收盘"].tolist()],
                    "source": "AKShare 东方财富",
                }
        except Exception as e:
            log.warning(f"验证K线[东财]{code}第{attempt + 1}次失败: {e}")
            await asyncio.sleep(0.5)

    # 回退①：新浪（全日期）
    try:
        import requests
        url = (
            f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
            f"CN_MarketData.getKLineData?symbol={prefix}{code}&scale=240&ma=no&datalen={max_days}"
        )
        r = await asyncio.to_thread(requests.get, url, headers=ua, timeout=10)
        series = r.json()
        if isinstance(series, list) and series:
            return {
                "dates": [x["day"][:10] for x in series],
                "closes": [round(float(x["close"]), 2) for x in series],
                "source": "新浪财经",
            }
    except Exception as e:
        log.warning(f"验证K线[新浪]{code}失败: {e}")

    # 回退②：腾讯（全日期）
    try:
        import requests
        url = (
            f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
            f"?param={prefix}{code},day,,,{max_days},qfq"
        )
        r = await asyncio.to_thread(requests.get, url, headers=ua, timeout=10)
        node = r.json().get("data", {}).get(f"{prefix}{code}", {})
        rows = node.get("qfqday") or node.get("day") or []
        if rows:
            return {
                "dates": [x[0][:10] for x in rows],
                "closes": [round(float(x[2]), 2) for x in rows],
                "source": "腾讯证券",
            }
    except Exception as e:
        log.warning(f"验证K线[腾讯]{code}失败: {e}")

    return None


async def verify_run(run_id: int) -> dict:
    """事后验证：对可提取股票代码的推演项，计算推演日至今实际涨跌并判定方向命中。

    返回 {"verifiable": [...], "unverifiable": [...], "hit_rate": xx%|"—"}，并回写存档。
    """
    run = storage.get_run(run_id)
    if not run:
        return {"error": "存档不存在"}
    payload = run["payload"]
    impacts = payload.get("impacts", [])
    start_date = run["created_at"][:10]

    code_map: dict[str, list[int]] = {}  # code -> impact indices
    unverifiable: list[int] = []
    for i, imp in enumerate(impacts):
        code = _extract_code(imp.get("target", ""))
        if code:
            code_map.setdefault(code, []).append(i)
        else:
            unverifiable.append(i)

    async def _verify_one(code: str) -> dict:
        k = await _kline_since(code, start_date)
        if not k:
            return {"code": code, "error": "K线数据不可用"}
        dates, closes = k["dates"], k["closes"]
        base_idx = next((j for j, d in enumerate(dates) if d >= start_date), None)
        if base_idx is None or base_idx >= len(closes) - 1:
            return {"code": code, "error": "推演日之后无足够行情数据"}
        base_close, latest_close = closes[base_idx], closes[-1]
        pct = round((latest_close / base_close - 1) * 100, 2)
        return {
            "code": code,
            "base_date": dates[base_idx],
            "base_close": base_close,
            "latest_date": dates[-1],
            "latest_close": latest_close,
            "pct_change": pct,
            "source": k["source"],
        }

    codes = list(code_map)
    results = await asyncio.gather(*[_verify_one(c) for c in codes])

    verifiable = []
    hits = 0
    total = 0
    for code, kres in zip(codes, results):
        for i in code_map[code]:
            imp = impacts[i]
            item = {
                "target": imp.get("target", ""),
                "direction": imp.get("direction"),
                "probability": imp.get("probability"),
                "code": code,
                **kres,
            }
            if "pct_change" in kres:
                actual_up = kres["pct_change"] > 0
                item["hit"] = (imp.get("direction") == "up") == actual_up
                total += 1
                hits += 1 if item["hit"] else 0
            verifiable.append(item)

    verify_payload = {
        "start_date": start_date,
        "verifiable": verifiable,
        "unverifiable_count": len(unverifiable),
        "hit_count": hits,
        "judgeable_count": total,
        "hit_rate": round(hits / total * 100, 1) if total else None,
    }
    storage.save_verification(run_id, verify_payload)
    return verify_payload
