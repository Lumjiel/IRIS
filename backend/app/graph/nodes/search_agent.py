"""
Function Calling Agent 节点
- LLM 自主决定何时调用工具、调用什么参数
- ToolNode 执行工具调用
- tools_condition 路由：agent → tools → agent → ... → END
"""
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from app.graph.state import AgentState
from app.tools.search_tools import search_web
from app.utils.llm import get_llm
from app.utils.logger import get_logger

log = get_logger("search_agent")

# 可用工具列表
TOOLS = [search_web]


def search_agent_node(state: AgentState) -> dict:
    """
    LLM 驱动的搜索 agent。
    与直接调用 search_tavily() 不同，这里 LLM 自主决定：
    1. 是否需要搜索（已有足够信息则不搜）
    2. 搜索什么关键词（基于 plan + query）
    3. 是否需要多轮搜索（评估已有结果是否充分）
    """
    query = state.get("query", "")
    plan = state.get("plan", [])
    messages = state.get("messages", [])

    # 构建系统提示词
    system_prompt = """你是一个专业的投研分析研究员。你的任务是通过网络搜索收集信息来回答用户的问题。

你有以下工具可用：
- search_web(query): 搜索互联网获取最新信息

工作原则：
1. 基于给定的搜索计划执行搜索
2. 每次搜索使用精准的关键词（公司名+关注维度）
3. 如果第一次搜索结果不理想，换关键词再搜一次
4. 最多搜索 5 次，足够时立即停止
5. 不需要搜索时直接输出总结"""

    # 构建用户消息
    user_content = f"用户问题: {query}\n\n搜索计划:\n" + "\n".join(f"- {p}" for p in plan)
    if messages:
        # 已有搜索历史，追加上下文
        user_content += "\n\n请评估已有搜索结果是否充分，如不充分请继续搜索。"

    # 组装消息列表
    all_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    # 获取带工具绑定的 LLM
    llm = get_llm(model_type="fast", node="researcher")
    llm_with_tools = llm.bind_tools(TOOLS)

    # 调用 LLM（Function Calling 核心）
    try:
        response = llm_with_tools.invoke(all_messages)
        log.info(f"[Function Calling] LLM 返回: tool_calls={response.tool_calls}, content={response.content[:100] if response.content else '(empty)'}")
    except Exception as e:
        log.error(f"[Function Calling] LLM 调用失败: {e}")
        # 降级：返回空结果
        return {"messages": [HumanMessage(content=f"搜索代理调用失败: {e}")]}

    return {"messages": [response]}


def search_tool_node(state: AgentState) -> dict:
    """执行 LLM 决定的工具调用（不依赖 langgraph.prebuilt）"""
    messages = state.get("messages", [])
    if not messages:
        return {"messages": []}
    
    last_msg = messages[-1]
    if not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
        return {"messages": []}
    
    # 执行所有工具调用
    tool_results = []
    for tc in last_msg.tool_calls:
        tool_name = tc.get("name", "")
        tool_args = tc.get("args", {})
        tool_id = tc.get("id", "")
        
        log.info(f"[ToolNode] 执行工具: {tool_name}({tool_args})")
        
        if tool_name == "search_web":
            result = search_web.invoke(tool_args)
        else:
            result = f"未知工具: {tool_name}"
        
        tool_results.append(
            ToolMessage(content=str(result), tool_call_id=tool_id, name=tool_name)
        )
    
    return {"messages": tool_results}

def route_after_tools(state: AgentState) -> dict:
    """
    工具执行后，提取搜索结果到 search_results。
    ToolNode 返回 {"messages": [...]}，我们把 ToolMessage 内容提取为 search_results。
    """
    messages = state.get("messages", [])
    search_results = []

    for msg in messages:
        if msg.type == "tool":
            content = msg.content
            if isinstance(content, str) and content:
                search_results.append(f"### 🌐 网络搜索结果\n{content}\n")

    log.info(f"[Function Calling] 提取了 {len(search_results)} 条搜索结果")
    return {"search_results": search_results}
