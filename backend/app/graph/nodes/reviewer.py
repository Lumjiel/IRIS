import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from app.utils.llm import llm_invoke
from app.graph.state import AgentState
from app.utils.logger import get_logger

log = get_logger("reviewer")


REVIEW_PROMPT = ChatPromptTemplate.from_template(
    """你是一个严厉的审核员。
    请检查以下报告是否充分回答了用户的问题：{query}

    报告内容：
    {report}

    请严格按照以下 JSON 格式返回结果（不要包含 Markdown 代码块）：
    {{
        "status": "PASS" 或 "FAIL",
        "feedback": "如果是 PASS，这里留空。如果是 FAIL，请列出 1 个具体的改进建议或需要补充搜索的方向。"
    }}
    """
)

def _clean_json_text(s: str) -> str:
    s = (s or "").strip()
    s = s.replace("```json", "").replace("```", "").strip()
    l = s.find("{")
    r = s.rfind("}")
    if l != -1 and r != -1 and r > l:
        s = s[l:r+1]
    return s

def review_node(state: AgentState):
    log.info("正在审查报告质量")
    query = state["query"]
    report = state["final_report"]

    num = state.get("revision_number", 0)

    response = llm_invoke(REVIEW_PROMPT.format(query=query, report=report).messages, model_type="smart")
    raw = response.content
    content = _clean_json_text(raw)

    result = None
    try:
        result = json.loads(content)
    except Exception as e1:
        retry_prompt = f'''
        你刚才的输出无法被 JSON 解析。
        请只输出一行合法 JSON，不要 Markdown，不要解释：
        {{"status":"PASS"或"FAIL","feedback":"PASS留空，FAIL给1条具体建议"}}

        用户问题：{query}
        报告：{report}
        '''
        retry_response = llm_invoke([HumanMessage(content=retry_prompt)], model_type="smart")
        retry_content = _clean_json_text(retry_response.content)
        try:
            result = json.loads(retry_content)
        except Exception as e2:
            log.warning(f"JSON解析失败，fail-closed。raw={raw!r}")
            result = {
                "status": "FAIL",
                "feedback": "审查器输出格式异常。请按要求重写报告，确保内容充分回答问题且结构清晰。"
            }

    return {
        "critique": result.get("feedback",""),
        "revision_number": num + 1,
        "review_status": result.get("status", "FAIL")
    }