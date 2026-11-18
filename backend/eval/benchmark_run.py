# -*- coding: utf-8 -*-
"""
IRIS 端到端 Benchmark 运行器（docs/benchmark.md 数据来源）

对 20 只样本股逐一发起真实研究请求（SSE），实测：
- 端到端延迟（请求发出 → [DONE]）
- 六章节完整率（报告含 一~六 章标题）
- 数据来源标注率（「来源」标注次数 / 经验阈值 4，上限 100%）
- Reviewer 首轮通过率（review_pass_first_try：首轮 review_status=PASS 且全程无 FAIL 回跳，
  逐轮采集实现；附 reviewer_rounds / review_final_status）
- Token 消耗（/api/usage 差值；real=provider 回传，est=流式字符估算）

用法：
    cd backend
    python -m eval.benchmark_run            # 跑全部 5 只
    python -m eval.benchmark_run --stocks 600196,000001
"""
import argparse
import json
import re
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000/api"
USER_ID = "benchmark"

STOCKS = [
    # === 首批 5 只（2026-08-24 / 2026-11-08 已实测，见 docs/benchmark.md）===
    ("600196", "复星医药"),
    ("000001", "平安银行"),
    ("600519", "贵州茅台"),
    ("000333", "美的集团"),
    ("601318", "中国平安"),
    # === 扩容 15 只（2026-11-10 注册，待真实环境实测补数）===
    ("300750", "宁德时代"),
    ("002594", "比亚迪"),
    ("600036", "招商银行"),
    ("000858", "五粮液"),
    ("601899", "紫金矿业"),
    ("688981", "中芯国际"),
    ("601012", "隆基绿能"),
    ("000651", "格力电器"),
    ("600276", "恒瑞医药"),
    ("601088", "中国神华"),
    ("600887", "伊利股份"),
    ("002415", "海康威视"),
    ("601888", "中国中免"),
    ("600030", "中信证券"),
    ("601988", "中国银行"),
]

CHAPTERS = ["一、核心结论", "二、公司概况", "三、财务分析", "四、行业观点", "五、风险提示", "六、投资建议"]
SOURCE_TAG_THRESHOLD = 4  # 经验阈值：概况/财务/行业/风险各至少一处来源标注


def usage_snapshot(reset=False):
    r = httpx.get(f"{BASE}/usage", params={"reset": reset}, timeout=15)
    return r.json()["usage"]


def ingest_event(ev: dict, acc: dict, now: float):
    """解析单条 SSE 事件，更新采集累加器 acc（纯函数，供单测回放）。

    两处历史坑（2026-11-19 修复，此前归档 node_elapsed 只剩 {'intent': 0.0}）：
    - 节点耗时：traced_* 包装经 emit_node_event 发出的 start/done 事件把 elapsed 挂在
      payload 顶层（utils/streaming.py），只有 routes 预跑路由的 intent 事件嵌在 data 里；
      旧代码只读 data["elapsed"]，per-node 耗时被整体丢弃。
    - 首轮通过：reviewer 每轮执行都会在 graph 流上发一条带 review_status 的节点更新
      事件（routes astream 透传 state_update），旧代码覆盖写只留最终状态，本模块
      文档声明的「PASS 且无 FAIL 回跳」从未真正实现。

    同一节点多轮执行（修订回跳场景）elapsed 按 step 累加：定位「修订轮耗时」要的是
    总量，轮数由 reviewer_rounds 单独给出，两者不混装。
    """
    step = ev.get("step", "")
    data = ev.get("data") or {}
    if step.endswith("_token") and acc["first_token_at"] is None and isinstance(data, dict) and data.get("token"):
        acc["first_token_at"] = now

    # elapsed 双形态：顶层（traced_* done 事件）/ data 嵌套（intent 预跑路由事件）
    elapsed = ev.get("elapsed")
    if elapsed is None and isinstance(data, dict):
        elapsed = data.get("elapsed")
    if isinstance(elapsed, (int, float)) and elapsed > 0:
        acc["node_elapsed"][step] = round(acc["node_elapsed"].get(step, 0.0) + elapsed, 2)

    if isinstance(data, dict):
        if step == "reviewer" and data.get("review_status"):
            acc["reviewer_statuses"].append(data["review_status"])
        if step == "writer" and data.get("final_report"):
            acc["final_report"] = data["final_report"]


def finalize_review(statuses: list[str]) -> tuple[bool, int, str]:
    """按模块文档声明实现首轮通过判定：首轮即 PASS 且全程无 FAIL 回跳。

    返回 (review_pass_first_try, reviewer_rounds, review_final_status)。
    旧实现是覆盖写只留最终状态——字段名与实现不符的问题在 2026-11-19 取证中暴露并修复。
    """
    first_try = bool(statuses) and statuses[0] == "PASS" and "FAIL" not in statuses
    return first_try, len(statuses), statuses[-1] if statuses else ""


def run_one(stock_code: str, name: str) -> dict:
    thread_id = f"bench-{stock_code}-{time.time():.0f}"  # 时间戳字符串，无类型转换
    body = {
        "query": f"研究一下 {stock_code} {name}的投资价值",
        "search_mode": "hybrid",
        "thread_id": thread_id,
        "style": "detailed",
        "language": "zh",
    }
    headers = {"Content-Type": "application/json", "X-User-Id": USER_ID}

    acc = {"first_token_at": None, "node_elapsed": {}, "reviewer_statuses": [], "final_report": ""}
    t0 = time.time()

    with httpx.stream("POST", f"{BASE}/chat", json=body, headers=headers,
                      timeout=httpx.Timeout(600, connect=15)) as resp:
        resp.raise_for_status()
        buffer = ""
        for chunk in resp.iter_text():
            buffer += chunk
            while "\n\n" in buffer:
                line_block, buffer = buffer.split("\n\n", 1)
                for line in line_block.split("\n"):
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:].strip()
                    if payload == "[DONE]":
                        continue
                    try:
                        ev = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    ingest_event(ev, acc, now=time.time() - t0)

    latency = round(time.time() - t0, 1)
    first_token_at = acc["first_token_at"]
    final_report = acc["final_report"]
    review_pass_first_try, reviewer_rounds, review_final_status = \
        finalize_review(acc["reviewer_statuses"])

    chapters_hit = sum(1 for c in CHAPTERS if c in final_report)
    chapter_rate = round(chapters_hit / len(CHAPTERS) * 100)
    source_tags = len(re.findall(r"来源[:：]", final_report))
    source_rate = min(100, round(source_tags / SOURCE_TAG_THRESHOLD * 100))
    report_chars = len(final_report)

    return {
        "code": stock_code,
        "name": name,
        "latency_s": latency,
        "first_token_s": round(first_token_at, 1) if first_token_at else None,
        "chapter_rate_pct": chapter_rate,
        "chapters_hit": f"{chapters_hit}/6",
        "source_rate_pct": source_rate,
        "source_tags": source_tags,
        "report_chars": report_chars,
        "review_pass_first_try": review_pass_first_try,
        "reviewer_rounds": reviewer_rounds,
        "review_final_status": review_final_status,
        "node_elapsed_s": {k: v for k, v in sorted(acc["node_elapsed"].items())},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stocks", default=None, help="逗号分隔的股票代码子集")
    args = parser.parse_args()

    stocks = STOCKS
    if args.stocks:
        wanted = set(args.stocks.split(","))
        stocks = [(c, n) for c, n in STOCKS if c in wanted]

    results = []
    for code, name in stocks:
        # 重置计数器：此后窗口从零累计（before 快照仅留档，不参与差值——
        # 差值口径会被上一轮的异步尾巴污染出负数）
        usage_snapshot(reset=True)
        print(f"[Run] {code} {name} ...", flush=True)
        row = run_one(code, name)
        time.sleep(4)  # 排水：等后台记忆写入等异步 LLM 调用落地，减少窗口串扰
        after = usage_snapshot()
        row["tokens_real_prompt"] = after["prompt"]
        row["tokens_real_completion"] = after["completion"]
        row["tokens_est_prompt"] = after["prompt_est"]
        row["tokens_est_completion"] = after["completion_est"]
        row["tokens_total"] = after["total_tokens"]
        results.append(row)
        print(f"  latency={row['latency_s']}s chapters={row['chapters_hit']} "
              f"src={row['source_tags']} tokens≈{row['tokens_total']}", flush=True)

    out = Path(__file__).parent / "reports" / "benchmark_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[Done] 结果已写入 {out}")


if __name__ == "__main__":
    main()
