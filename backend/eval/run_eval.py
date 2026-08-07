"""Agent 评估运行器。

对每个用例跑一遍完整 graph，统计：reviewer 通过率、报告是否 grounded（有实测内容）、
引用数、篇幅、是否落入防幻觉兜底。输出逐条结果 + 汇总。

用法（backend/ 目录下）：
    python -m eval.run_eval
需要真实 LLM 与搜索 key（参考 backend/.env）。
"""
import asyncio
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # backend/
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.graph.graph import create_graph
from eval.cases import EVAL_CASES

FALLBACK_MARK = "未能检索到"  # 防幻觉兜底文案特征


def _base_state(query: str) -> dict:
    return {
        "query": query,
        "revision_number": 0,
        "search_mode": "hybrid",
        "preferences": {"style": "concise", "language": "zh"},
        "plan": [], "plan_structure": [], "search_results": [], "research_findings": [],
        "synthesis": "", "critique": "", "review_status": "PASS", "should_stop": False,
        "active_skill": "", "intent": "", "intent_confidence": 0.0, "is_followup": False,
        "entities": [], "clarify_question": "", "conversation_summary": "", "final_report": "",
        "search_sources": [], "citation_refs": "", "grounded": True,
        "pending_hitl": False, "hitl_choice": "", "hitl_question": "", "hitl_mode": "",
    }


async def run_case(case: dict) -> dict:
    app = create_graph()
    final_report = ""
    grounded = True
    review_status = "UNKNOWN"
    t0 = time.time()
    try:
        async for event in app.astream(
            _base_state(case["query"]),
            config={"configurable": {"thread_id": f"eval-{case['name']}"}},
        ):
            for node, upd in event.items():
                if node == "writer" and upd.get("final_report"):
                    final_report = upd["final_report"]
                    grounded = upd.get("grounded", True)
                elif node == "reviewer":
                    review_status = upd.get("review_status", review_status)
    except asyncio.TimeoutError:
        review_status = "TIMEOUT"
    except Exception as e:
        review_status = f"ERROR:{type(e).__name__}"

    duration = round(time.time() - t0)
    citations = len(re.findall(r"\[\d+\]", final_report))
    fellback = FALLBACK_MARK in final_report
    length = len(final_report)

    ok_length = length >= case.get("min_length", 300)
    ok_sources = (not case.get("require_sources", False)) or citations > 0
    ok_grounded = grounded and not fellback
    ok_review = review_status == "PASS"
    passed = ok_review and ok_length and ok_grounded and ok_sources

    return {
        "case": case["name"],
        "passed": passed,
        "reviewer": review_status,
        "grounded": grounded,
        "fell_back": fellback,
        "length": length,
        "citations": citations,
        "duration_s": duration,
        "ok_length": ok_length,
        "ok_sources": ok_sources,
    }


async def main():
    results = []
    for case in EVAL_CASES:
        print(f"▶ 运行用例: {case['name']} ...", flush=True)
        r = await run_case(case)
        results.append(r)
        print("  " + json.dumps(r, ensure_ascii=False), flush=True)

    print("\n=== 汇总 ===")
    passed = sum(1 for r in results if r["passed"])
    print(f"通过: {passed}/{len(results)}")
    print(f"reviewer 通过率: {sum(1 for r in results if r['reviewer']=='PASS')}/{len(results)}")
    print(f"grounded 率: {sum(1 for r in results if r['grounded'] and not r['fell_back'])}/{len(results)}")
    print(f"平均篇幅: {sum(r['length'] for r in results)//max(1,len(results))} 字符")
    print(f"平均引用: {sum(r['citations'] for r in results)/max(1,len(results)):.1f}")
    print(f"平均耗时: {sum(r['duration_s'] for r in results)/max(1,len(results)):.0f}s")


if __name__ == "__main__":
    asyncio.run(main())