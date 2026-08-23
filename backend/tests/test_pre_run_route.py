"""routes.py 预跑路由集成测试。

覆盖链路：checkpoint 持久化 final_report → _pre_run_route 经 aget_state 读取 →
route_query 判定。对抗式审查反例验证证明：把 checkpoint 读法改回 initial_state
兜底后全量 pytest 仍全绿（135 passed），即存量测试对该路径零覆盖——本文件补上。
"""
from unittest.mock import MagicMock, patch

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.api.routes import _pre_run_route
from app.graph.graph import create_graph


@pytest.fixture
async def app(_mock_env_vars):
    """内存 SQLite checkpoint + 完整图（不触发任何节点执行）。"""
    async with AsyncSqliteSaver.from_conn_string(":memory:") as memory:
        yield create_graph(memory=memory)


class TestPreRunRoute:
    """_pre_run_route：SSE 端点首事件 intent 的数据来源。"""

    async def test_second_turn_refine_detected_from_checkpoint(self, app):
        """核心回归：首轮报告持久化后，二轮追问必须判为 refiner 而非 chat。

        注意：aupdate_state 会触发条件入口的 router 分支求值，故 update 载荷必须含
        query 字段，且全程 mock llm_invoke（入口路由可能走 LLM 分类）。
        """
        config = {"configurable": {"thread_id": "test-prerun-refine"}}
        with patch("app.graph.nodes.router.llm_invoke") as mock_llm:
            mock_llm.return_value = MagicMock(content="REFINE")
            await app.aupdate_state(
                config,
                {"query": "分析复星医药", "final_report": "## 深度研报\n\n（正文……）"},
            )
            route, has_report = await _pre_run_route(
                app, config, "请补充公司面临的主要风险因素"
            )
        assert has_report is True
        assert route == "refiner"

    async def test_second_turn_new_research_with_report(self, app):
        """有报告 + 全新研究课题 → planner（LLM 分类 RESEARCH 分支）。"""
        config = {"configurable": {"thread_id": "test-prerun-research"}}
        with patch("app.graph.nodes.router.llm_invoke") as mock_llm:
            mock_llm.return_value = MagicMock(content="RESEARCH")
            await app.aupdate_state(
                config, {"query": "旧课题", "final_report": "旧报告内容"}
            )
            route, has_report = await _pre_run_route(app, config, "分析宁德时代")
        assert has_report is True
        assert route == "planner"

    async def test_first_turn_empty_checkpoint_routes_without_report(self, app):
        """全新 thread 无 checkpoint 数据 → 视为无报告，研究动词直接命中 planner。"""
        config = {"configurable": {"thread_id": "test-prerun-fresh"}}
        route, has_report = await _pre_run_route(app, config, "分析一下宁德时代")
        assert has_report is False
        assert route == "planner"

    async def test_snapshot_read_failure_degrades_to_no_report(self, app):
        """aget_state 异常时降级为无报告路径而非抛出（SSE 首事件不能失败）。"""
        config = {"configurable": {"thread_id": "test-prerun-error"}}

        async def _boom(cfg):
            raise RuntimeError("db locked")

        with patch.object(type(app), "aget_state", _boom):
            route, has_report = await _pre_run_route(
                app, config, "分析一下宁德时代"
            )
        assert has_report is False
        assert route == "planner"
