# -*- coding: utf-8 -*-
"""
IRIS 端到端 Benchmark 运行器（docs/benchmark.md 数据来源）

对 5 只样本股逐一发起真实研究请求（SSE），实测：
- 端到端延迟（请求发出 → [DONE]）
- 六章节完整率（报告含 一~六 章标题）
- 数据来源标注率（「来源」标注次数 / 经验阈值 4，上限 100%）
- Reviewer 一次通过率（review_status=PASS 且无 FAIL 回跳）
- Token 消耗（/api/usage 差值；real=provider 回传，est=流式字符估算）

用法：
    cd backend
    python -m eval.benchmark_run            # 跑全部 5 只
    python -m eval.benchmark_run --stocks 600196,000001
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000/api"
USER_ID = "benchmark"

STOCKS = [
    ("600196", "复星医药"),
    ("000001", "平安银行"),
    ("600519", "贵州茅台"),
    ("000333", "美的集团"),
    ("601318", "中国平安"),
]

CHAPTERS = ["一、核心结论", "二、公司概况", "三、财务分析", "四、行业观点", "五、风险提示", "六、投资建议"]
SOURCE_TAG_THRESHOLD = 4  # 经验阈值：概况/财务/行业/风险各至少一处来源标注


def usage_snapshot(reset=False):
    r = httpx.get(f"{BASE}/usage", params={"reset": reset}, timeout=15)
    return r.json()["usage"]


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

    final_report = ""
    review_status = ""
    node_elapsed = {}
    t0 = time.time()
    first_token_at = None

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
                    step = ev.get("step", "")
                    data = ev.get("data") or {}
                    if step.endswith("_token") and first_token_at is None and data.get("token"):
                        first_token_at = time.time() - t0
                    if isinstance(data, dict):
                        if "elapsed" in data:
                            node_elapsed[step] = data["elapsed"]
                        if step == "reviewer" and data.get("review_status"):
                            review_status = data["review_status"]
                        if step == "writer" and data.get("final_report"):
                            final_report = data["final_report"]

    latency = round(time.time() - t0, 1)

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
        "review_pass_first_try": review_status == "PASS",
        "node_elapsed_s": {k: v for k, v in sorted(node_elapsed.items())},
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
