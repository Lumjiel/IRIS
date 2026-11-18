# -*- coding: utf-8 -*-
"""benchmark_run 采集逻辑单测（合成 SSE 事件回放，无需真实后端与 LLM key）。

背景（2026-11-19）：benchmark_run.py 存在两个采集 bug——
1. per-node elapsed schema 错配：traced_* 事件 elapsed 在 payload 顶层，
   旧代码只读 data["elapsed"]，归档只剩 {'intent': 0.0}；
2. review_pass_first_try 覆盖写只留最终状态，声明的「PASS 且无 FAIL 回跳」未实现。
本测试用合成事件序列锁定修复后的采集契约。
"""
from eval.benchmark_run import ingest_event, finalize_review


def make_acc():
    return {"first_token_at": None, "node_elapsed": {}, "reviewer_statuses": [], "final_report": ""}


def test_node_elapsed_top_level():
    """traced_* done 事件：elapsed 在 payload 顶层，必须被采集。"""
    acc = make_acc()
    ingest_event({"step": "router", "status": "start"}, acc, now=0.1)
    ingest_event({"step": "router", "status": "done", "elapsed": 1.23}, acc, now=1.33)
    ingest_event({"step": "planner", "status": "done", "elapsed": 2.05}, acc, now=3.38)
    assert acc["node_elapsed"] == {"router": 1.23, "planner": 2.05}


def test_node_elapsed_nested_intent():
    """intent 预跑路由事件：elapsed 嵌套在 data 里（routes.py 直发），同样必须被采集。"""
    acc = make_acc()
    ingest_event({"step": "intent", "data": {"intent": "research", "route": "planner", "elapsed": 0.42}},
                 acc, now=0.42)
    assert acc["node_elapsed"] == {"intent": 0.42}


def test_node_elapsed_multi_round_accumulates():
    """修订回跳场景：同一节点多轮执行按 step 累加（定位修订耗时需要总量）。"""
    acc = make_acc()
    ingest_event({"step": "writer", "status": "done", "elapsed": 30.0}, acc, now=30.0)
    ingest_event({"step": "writer", "status": "done", "elapsed": 12.5}, acc, now=42.5)
    assert acc["node_elapsed"] == {"writer": 42.5}


def test_node_elapsed_ignores_zero_and_missing():
    """start 事件无 elapsed、done elapsed=0 都不落账（与旧归档 {'intent': 0.0} 的假数据划清界限）。"""
    acc = make_acc()
    ingest_event({"step": "researcher", "status": "start"}, acc, now=0.0)
    ingest_event({"step": "researcher", "status": "done"}, acc, now=1.0)
    assert acc["node_elapsed"] == {}


def test_first_token():
    acc = make_acc()
    ingest_event({"step": "writer_token", "data": {"token": "一"}}, acc, now=2.7)
    ingest_event({"step": "writer_token", "data": {"token": "、"}}, acc, now=2.8)
    assert acc["first_token_at"] == 2.7


def test_reviewer_statuses_collected_per_round():
    """reviewer 每轮执行的 review_status 都进列表，不再覆盖写。"""
    acc = make_acc()
    ingest_event({"step": "reviewer", "data": {"review_status": "FAIL", "critique": "财务数据不足"}},
                 acc, now=10.0)
    ingest_event({"step": "reviewer", "data": {"review_status": "FAIL", "critique": "缺风险提示"}},
                 acc, now=20.0)
    ingest_event({"step": "reviewer", "data": {"review_status": "PASS", "critique": ""}},
                 acc, now=30.0)
    assert acc["reviewer_statuses"] == ["FAIL", "FAIL", "PASS"]


def test_final_report_last_write_wins():
    acc = make_acc()
    ingest_event({"step": "writer", "data": {"final_report": "初稿"}}, acc, now=1.0)
    ingest_event({"step": "writer", "data": {"final_report": "修订稿"}}, acc, now=2.0)
    assert acc["final_report"] == "修订稿"


def test_finalize_review_first_try_pass():
    assert finalize_review(["PASS"]) == (True, 1, "PASS")


def test_finalize_review_fail_bounce():
    assert finalize_review(["FAIL", "FAIL", "PASS"]) == (False, 3, "PASS")


def test_finalize_review_reviewer_never_ran():
    """chat/refine 等路由不经过 reviewer：首轮通过=False、轮数=0、终态空（与旧行为一致）。"""
    assert finalize_review([]) == (False, 0, "")
