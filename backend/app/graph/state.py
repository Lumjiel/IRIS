from typing import TypedDict, List

class AgentState(TypedDict):
    """
    Agent 的状态定义。
    这就好比一个共享的文件夹，每个步骤都可以往里面存取东西。
    """
    query: str                # 用户原始问题
    plan: List[str]           # 规划的搜索步骤
    search_results: List[str] # 搜索到的具体内容
    final_report: str         # 最终生成的报告
    critique: str             # 审查意见
    revision_number: int      # 当前修改到了第几版 (防止死循环)
    review_status: str        # "PASS" 或 "FAIL"
    search_mode: str          # 取值: "document" (只查文档) 或 "hybrid" (混合搜索)
    should_stop: bool         # 控制位

    # === 意图分类 ===
    # intent: router 分类结果，取值: research / chat / sql / tool_call / refine / clarify
    intent: str
    # intent_confidence: 分类置信度 0.0-1.0，由 router 填充
    intent_confidence: float
    # is_followup: 是否为对上一轮的续聊（短回复/代词等），由 router 判断
    is_followup: bool
    # entities: 从用户输入中抽取的关键实体（人名/产品/专有名词等），由 router 填充
    entities: list

    # === 目标规划 ===
    # plan_structure: 结构化研究计划 [{subtask, queries}]，由 planner 填充
    # plan: 拍平的搜索子问题（由 plan_structure 派生），向后兼容 extractor 等下游
    plan_structure: list
    # research_findings: Researcher 按子任务分组的结构化检索结果，供 Synthesize 节点汇总
    research_findings: list
    # search_error: 所有网络搜索均因基础设施原因失败（API key 失效/网络/配额）时为 True
    search_error: bool
    # synthesis: Planner 拆解 -> Researcher 并行检索 -> Synthesize 汇总后的关键发现摘要
    synthesis: str

    # === 意图澄清 ===
    # clarify_question: router 判为 CLARIFY 时，clarify 节点向用户抛出的澄清问题
    clarify_question: str

    # === 防幻觉 (Grounded) ===
    # grounded: writer 的报告是否有实际检索内容支撑（true=有据可依, false=信息不足诚实说明）
    grounded: bool

    # === Human-in-the-loop ===
    # pending_hitl: reviewer 首次 FAIL 后是否暂停等用户决策
    pending_hitl: bool
    # hitl_choice: 前端传回的 HITL 决策（retry / use_existing / redirect）
    hitl_choice: str
    # hitl_question: hitl_gate 节点抛给用户的澄清问题/选项
    hitl_question: str
    # hitl_mode: apply_hitl 的临时路由信号（planner=重规划 / end=定稿）
    hitl_mode: str

    # === ReAct 工具调用 ===
    # tool_messages: ReAct 推理轨迹 [{role, content}]，tool_call/tool_execute 读写
    tool_messages: list
    # tool_iterations: 已执行工具轮数，达到 MAX_TOOL_ITERATIONS 强制出答案
    tool_iterations: int
    # tool_call_request: 当前待执行的工具请求 {tool, arguments}；None 表示直接回答
    tool_call_request: dict

    # === 记忆系统 ===
    # conversation_summary: @deprecated — 四层记忆系统（Episodic/Semantic/Procedural）已替代此字段
    # 保留字段以维持 LangGraph checkpoint 兼容性，不再由 writer/refiner 更新
    conversation_summary: str

    # === 用户偏好 ===
    # preferences: {style, language}，从前端传递，影响 writer 输出风格
    preferences: dict

    # === Skill 系统 ===
    # active_skill: 匹配到的 Skill 名称，为空表示使用默认策略
    active_skill: str

    # === 引用系统 ===
    # search_sources: 搜索来源列表，由 researcher 填充，writer 用于生成引用标注
    search_sources: List[dict]
    # citation_refs: 累积的引用标注文本，跨轮持久化（审查 FAIL 回跳后保留前轮引用）
    citation_refs: str