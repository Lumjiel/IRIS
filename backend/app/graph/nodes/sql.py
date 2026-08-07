from langchain_core.messages import HumanMessage, SystemMessage
from app.utils.llm import llm_invoke
from app.utils.streaming import llm_stream_tokens, get_token_queue
from app.graph.state import AgentState
from app.utils.logger import get_logger

log = get_logger("sql")

SQL_PROMPT = """\
你是一个 SQL 专家。根据用户的描述，生成对应的 SQL 查询语句。

规则：
1. 只输出 SQL 语句，不要有其他解释
2. 使用标准 SQL 语法（兼容 MySQL/PostgreSQL/SQLite）
3. 如果用户没有指定数据库，默认使用通用语法
4. 如果用户的描述不清晰，生成最合理的 SQL 并加注释说明
5. 对于复杂查询，使用适当的 JOIN、子查询、窗口函数等
6. 注意 SQL 注入防护，使用参数化查询的占位符"""


async def sql_node(state: AgentState):
    """SQL 生成节点：根据用户描述生成 SQL 语句"""
    query = state["query"]
    log.info(f"SQL 模式: {query[:50]}...")

    messages = [SystemMessage(content=SQL_PROMPT), HumanMessage(content=query)]

    if get_token_queue() is not None:
        sql_response = await llm_stream_tokens(
            messages, model_type="fast", node_name="sql", node="sql"
        )
    else:
        sql_response = llm_invoke(messages, node="sql").content

    # 格式化输出
    report = f"## SQL 查询\n\n```sql\n{sql_response.strip()}\n```"
    return {"final_report": report}
