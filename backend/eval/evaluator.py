"""
IRIS Eval 评测运行器
- 加载 Golden Case 数据集
- 运行评测并生成报告
- 支持 LLM-as-Judge 和确定性规则
"""
import yaml
import json
import time
from pathlib import Path
from typing import Any

from app.graph import create_graph
from app.graph.state import AgentState
from app.utils.llm import llm_invoke
from app.utils.logger import get_logger

log = get_logger("eval")

GOLDEN_CASES_PATH = Path(__file__).parent / "golden_cases.yaml"


def load_golden_cases() -> list[dict]:
    """加载 Golden Case 数据集"""
    with open(GOLDEN_CASES_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("test_cases", [])


def run_eval(
    graph,
    golden_cases: list[dict],
    output_path: str = "eval/reports/eval_report.json",
) -> dict:
    """
    运行评测
    
    Args:
        graph: 编译后的 LangGraph 图
        golden_cases: Golden Case 列表
        output_path: 评测报告输出路径
    
    Returns:
        评测结果摘要
    """
    results = []
    total_score = 0.0
    total_cases = len(golden_cases)
    
    for case in golden_cases:
        case_id = case.get("id", "unknown")
        query = case.get("query", "")
        expected_topics = case.get("expected_topics", [])
        min_length = case.get("min_report_length", 0)
        expected_error = case.get("expected_error")
        
        log.info(f"[Eval] 运行用例: {case_id} | 查询: {query[:50]}...")
        
        start_time = time.time()
        
        try:
            # 运行图
            config = {"configurable": {"thread_id": f"eval-{case_id}"}}
            result = graph.invoke({"query": query}, config=config)
            
            elapsed = time.time() - start_time
            
            # 提取结果
            final_report = result.get("final_report", "")
            review_status = result.get("review_status", "FAIL")
            revision_number = result.get("revision_number", 0)
            
            # === 评分 ===
            score = 0.0
            details = {}
            
            # 1. 检查预期错误
            if expected_error:
                if expected_error == "empty_query" and not final_report:
                    score = 1.0
                    details["error_check"] = "passed"
                elif expected_error == "whitespace_only" and not final_report:
                    score = 1.0
                    details["error_check"] = "passed"
                else:
                    score = 0.0
                    details["error_check"] = "failed"
            else:
                # 2. 检查报告长度
                length_ok = len(final_report) >= min_length
                details["length_check"] = {
                    "expected": min_length,
                    "actual": len(final_report),
                    "passed": length_ok,
                }
                
                # 3. 检查主题覆盖
                topic_hits = [t for t in expected_topics if t in final_report]
                topic_coverage = len(topic_hits) / len(expected_topics) if expected_topics else 1.0
                details["topic_coverage"] = {
                    "expected": expected_topics,
                    "hits": topic_hits,
                    "coverage": topic_coverage,
                }
                
                # 4. 综合评分
                score = (
                    (1.0 if length_ok else 0.0) * 0.3 +
                    topic_coverage * 0.5 +
                    (1.0 if review_status == "PASS" else 0.5) * 0.2
                )
                
                details["review_status"] = review_status
                details["revision_number"] = revision_number
            
            total_score += score
            
            results.append({
                "id": case_id,
                "query": query,
                "score": score,
                "elapsed": elapsed,
                "passed": score >= 0.6,
                "details": details,
            })
            
            log.info(f"[Eval] {case_id}: score={score:.2f}, elapsed={elapsed:.1f}s")
            
        except Exception as e:
            elapsed = time.time() - start_time
            log.error(f"[Eval] {case_id} 失败: {e}")
            results.append({
                "id": case_id,
                "query": query,
                "score": 0.0,
                "elapsed": elapsed,
                "passed": False,
                "error": str(e),
            })
    
    # 汇总
    avg_score = total_score / total_cases if total_cases > 0 else 0.0
    passed_count = sum(1 for r in results if r.get("passed"))
    
    summary = {
        "total_cases": total_cases,
        "passed": passed_count,
        "failed": total_cases - passed_count,
        "average_score": avg_score,
        "pass_rate": passed_count / total_cases if total_cases > 0 else 0.0,
        "results": results,
    }
    
    # 保存报告
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    log.info(f"[Eval] 评测完成: avg_score={avg_score:.2f}, pass_rate={summary['pass_rate']:.2f}")
    
    return summary


if __name__ == "__main__":
    # 独立运行评测
    from app.graph.checkpoint import get_memory
    
    graph = create_graph(memory=get_memory())
    cases = load_golden_cases()
    summary = run_eval(graph, cases)
    
    print(f"\n=== 评测结果 ===")
    print(f"总用例: {summary['total_cases']}")
    print(f"通过: {summary['passed']}")
    print(f"失败: {summary['failed']}")
    print(f"平均分: {summary['average_score']:.2f}")
    print(f"通过率: {summary['pass_rate']:.2f}")
