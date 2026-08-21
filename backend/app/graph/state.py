from typing import TypedDict, List, Annotated
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Agent 的状态定义。
    这就好比一个共享的文件夹，每个步骤都可以往里面存取东西。
    """
    query: str                # 用户原始问题
    messages: Annotated[List, add_messages]  # Function Calling 消息历史（自动累加）
    search_results: List[str] # 搜索到的具体内容
    final_report: str         # 最终生成的报告
    critique: str             # 审查意见
    revision_number: int      # 当前修改到了第几版 (防止死循环)
    review_status: str        # "PASS" 或 "FAIL"
    search_mode: str          # 取值: "document" (只查文档) 或 "hybrid" (混合搜索)
    should_stop: bool         # 控制位

    # === 记忆系统 ===
    # conversation_summary: 运行摘要，由 writer/refiner 每轮增量更新
    # 通过 checkpoint 自动持久化，不需要额外存储
    conversation_summary: str

    # === 用户偏好 ===
    # preferences: {style, language}，从前端传递，影响 writer 输出风格
    # === Function Calling 容错 (新增) ===
    # error_code: 结构化错误码（ErrorCode 枚举值）
    error_code: str
    # degraded: 是否处于降级模式
    degraded: bool
    # failed_tools: 失败的工具列表
    failed_tools: List[str]
    # early_stop: reviewer 设置的早停标记
    early_stop: bool
    # should_continue: 条件边控制
    should_continue: bool
    # report_history: reviewer 维护的报告历史（用于 cosine 相似度）
    report_history: List[str]
    # tool_status: 工具调用状态 {name: {success, error}}
    tool_status: dict
    preferences: dict

    # === 金融数据（阶段 2 新增） ===
    # financial_data: AKShare 拉取的结构化金融数据
    # 典型结构: {"stock_code": "600196", "stock_info": {...}, "indicators": {...}, "quote": {...}}
    financial_data: dict
    # data_sources: 数据来源列表 ["AKShare/东方财富", "PDF研报", "Tavily"]
    data_sources: List[str]
    # pending_stock_code: 待分析股票代码（router/planner 提取 → data_collector 消费）
    pending_stock_code: str