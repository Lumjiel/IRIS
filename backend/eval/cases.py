"""Agent 评估用例集 — 衡量 IRIS 整体输出质量，而非单个函数。

每个用例定义：查询、期望的最小篇幅、是否要求引用来源。
运行 `python -m eval.run_eval`（需真实 LLM + 搜索 key）。
"""

EVAL_CASES = [
    {
        "name": "量子计算趋势",
        "query": "分析量子计算近年来的发展趋势",
        "min_length": 300,
        "require_sources": True,
    },
    {
        "name": "大模型幻觉",
        "query": "调研大模型幻觉问题及主流缓解方法",
        "min_length": 300,
        "require_sources": True,
    },
    {
        "name": "RAG 技术",
        "query": "调研 RAG 检索增强生成的技术原理、局限与改进方向",
        "min_length": 300,
        "require_sources": True,
    },
    {
        "name": "多 Agent 框架",
        "query": "对比 LangGraph 与 CrewAI 多 Agent 框架的差异",
        "min_length": 300,
        "require_sources": True,
    },
    {
        "name": "数据库选型",
        "query": "PostgreSQL 与 MySQL 的选型对比",
        "min_length": 300,
        "require_sources": True,
    },
]