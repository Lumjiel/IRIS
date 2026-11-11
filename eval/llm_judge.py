#!/usr/bin/env python3
"""LLM-as-Judge：对 IRIS 产出的中文研报做结构化评分。

GOAL 澄清（2026-11-11）：报告质量用 LLM 当裁判 + 人工校准。
用法：
    backend/.venv/bin/python eval/llm_judge.py <report.md> [--out results.json]

评分维度（各 0-10 + 依据引文，要求裁判引用原文片段防止空泛打分）：
  1. structure    六章节结构完整性（核心结论/公司概况/财务分析/行业观点/风险提示/投资建议）
  2. sourcing     来源标注密度与规范性（[来源: ...]）
  3. honesty      诚实标注（数据不足用 ⚠️ 而非编造；数据-观点分离）
  4. compliance   投资建议合规性（不构成投资建议、免责声明、无目标价/评级越界）
  5. readability  中文表达与逻辑连贯

环境变量：OPENAI_API_BASE / OPENAI_API_KEY / LLM_MODEL_PRIMARY，
或 --env 指定 .env 文件自动读取（默认不读，显式传入才读，密钥不打印不落盘）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

RUBRIC = """你是投研报告质量裁判。对下面这份 A 股研究报告严格评分。每个维度给 0-10 分并引用报告原文片段作为依据（不许空泛打分）。数据类字段必须核对一致性描述而非编造。

维度定义：
1. structure 六章节结构完整性：核心结论/公司概况/财务分析/行业观点/风险提示/投资建议是否齐备
2. sourcing 来源标注：数据是否带 [来源: ...] 标注，标注是否规范、可追溯
3. honesty 诚实标注：数据缺失是否用 ⚠️ 明示而非编造；表格数据与观点是否分离；是否夸大
4. compliance 合规性：是否含「不构成投资建议」类免责声明；是否越界给出目标价/买卖指令
5. readability 中文表达：逻辑连贯、术语准确、无自相矛盾

输出严格 JSON（不要 markdown 代码块）：
{"scores": {"structure": {"score": 0, "evidence": "引文"}, ...五个维度...},
 "overall": 0, "verdict": "一句话总评"}"""

PROMPT_TMPL = """{rubric}

==== 待评报告 ====
{report}
==== 报告结束 ===="""


def load_env(path: str) -> None:
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def judge(report: str, timeout: int = 180) -> dict:
    import requests

    base = os.environ["OPENAI_API_BASE"].rstrip("/")
    key = os.environ["OPENAI_API_KEY"]
    model = os.environ.get("LLM_MODEL_PRIMARY", "qwen-plus")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": RUBRIC},
            {"role": "user", "content": PROMPT_TMPL.format(rubric=RUBRIC, report=report[:30000])},
        ],
        "temperature": 0,
    }
    t0 = time.time()
    r = requests.post(f"{base}/chat/completions", json=payload,
                      headers={"Authorization": f"Bearer {key}"}, timeout=timeout)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    usage = r.json().get("usage", {})
    elapsed = round(time.time() - t0, 1)

    # 容忍模型裹 markdown 代码块
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`").removeprefix("json").strip()
    try:
        verdict = json.loads(content)
    except json.JSONDecodeError:
        verdict = {"raw": content[:2000], "parse_error": True}

    return {"model": model, "elapsed_s": elapsed, "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"), "judge": verdict}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("report", help="研报 markdown 路径")
    ap.add_argument("--env", help=".env 文件路径（显式传入才读）")
    ap.add_argument("--out", help="结果 JSON 输出路径")
    args = ap.parse_args()

    if args.env:
        load_env(args.env)
    for k in ("OPENAI_API_BASE", "OPENAI_API_KEY"):
        if not os.environ.get(k):
            print(f"缺环境变量 {k}（或用 --env 指定 .env）", file=sys.stderr)
            return 2

    report = Path(args.report).read_text(encoding="utf-8")
    result = judge(report)
    result["report_path"] = str(args.report)
    result["report_chars"] = len(report)
    out = json.dumps(result, ensure_ascii=False, indent=1)
    if args.out:
        Path(args.out).write_text(out, encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
