"""
IRIS Reviewer 节点
- 质量审查（JSON 输出 + 重试 + fail-closed）
- Cosine 相似度早停（防止 refiner 循环死锁）
"""
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from app.utils.llm import llm_invoke
from app.graph.state import AgentState
from app.utils.logger import get_logger
from app.config import MAX_REVISIONS

log = get_logger("reviewer")

REVIEW_PROMPT = ChatPromptTemplate.from_template(
    """你是一个严厉的监督员。
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


def _compute_cosine_similarity(text1: str, text2: str) -> float:
    """
    计算两个文本的 cosine 相似度
    使用 sklearn 的 TfidfVectorizer + cosine_similarity
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return float(similarity)
    except ImportError:
        log.warning("sklearn 未安装，跳过 cosine 相似度计算")
        return 0.0
    except Exception as e:
        log.warning(f"cosine 计算失败: {e}")
        return 0.0


def review_node(state: AgentState):
    """
    审查报告质量
    
    新增逻辑：
    1. 维护 report_history 列表
    2. 计算当前报告与上一版的 cosine 相似度
    3. 相似度 > 0.95 → 早停，避免 refiner 循环死锁
    """
    log.info("正在审查报告质量")
    query = state["query"]
    report = state.get("final_report", "")
    
    if not report or len(report.strip()) < 50:
        log.warning("报告内容过短或为空，直接判 FAIL")
        return {
            "critique": "报告内容不完整或为空，请重新生成。",
            "revision_number": state.get("revision_number", 0) + 1,
            "review_status": "FAIL",
            "early_stop": False,
            "should_continue": True,
        }
    
    num = state.get("revision_number", 0)
    
    num = state.get("revision_number", 0)
    report_history = state.get("report_history", [])
    
    # === Cosine 相似度早停 ===
    early_stop = False
    similarity = 0.0
    
    if report_history:
        previous_report = report_history[-1]
        similarity = _compute_cosine_similarity(report, previous_report)
        log.info(f"[Reviewer] 与上一版报告的 cosine 相似度: {similarity:.4f}")
        
        if similarity > 0.95:
            early_stop = True
            log.warning(
                f"[Reviewer] 相似度 {similarity:.4f} > 0.95，判定为无法进一步改进，"
                f"触发早停（第 {num + 1} 次审查）"
            )
    
    # 更新历史
    report_history.append(report)
    state["report_history"] = report_history
    
    # 如果触发早停，直接返回 PASS 并标记
    if early_stop:
        return {
            "critique": f"连续两版报告相似度 {similarity:.4f} > 0.95，判定为无法进一步改进，强制结束循环。",
            "revision_number": num + 1,
            "review_status": "PASS",
            "early_stop": True,
            "should_continue": False,
        }
    
    # === 原有审查逻辑 ===
    response = llm_invoke(
        [HumanMessage(content=REVIEW_PROMPT.format(query=query, report=report))],
        model_type="smart",
        node="reviewer"
    )
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
        retry_response = llm_invoke(
            [HumanMessage(content=retry_prompt)],
            model_type="smart",
            node="reviewer"
        )
        retry_content = _clean_json_text(retry_response.content)
        try:
            result = json.loads(retry_content)
        except Exception as e2:
            log.warning(f"JSON解析失败，fail-closed。raw={raw!r}")
            result = {
                "status": "FAIL",
                "feedback": "审查器输出格式异常。请按要求重写报告，确保内容充分回答问题且结构清晰。"
            }
    
    review_result = {
        "critique": result.get("feedback", ""),
        "revision_number": num + 1,
        "review_status": result.get("status", "FAIL"),
        "early_stop": False,
        "should_continue": result.get("status", "FAIL") == "FAIL",
        "similarity": similarity,
    }
    
    return review_result
