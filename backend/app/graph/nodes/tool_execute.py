"""
ReAct 工具调用 - 执行节点。

读取 tool_call 节点产出的 tool_call_request，执行对应工具，把结果追加到
tool_messages（ReAct 推理轨迹），随后回到 tool_call 节点继续决策。
"""
import json

from app.graph.state import AgentState
from app.tools.registry import ToolRegistry
from app.utils.logger import get_logger

log = get_logger("tool_execute")


def tool_execute_node(state: AgentState) -> dict:
    request = state.get("tool_call_request")
    if not request:
        log.warning("tool_execute 收到空请求")
        return {}

    tool_name = request.get("tool", "")
    arguments = request.get("arguments") or {}
    if not isinstance(arguments, dict):
        arguments = {"query": str(arguments)}

    tool = ToolRegistry.get(tool_name)
    if tool is None:
        result_text = f"错误：工具 '{tool_name}' 不存在或未注册。"
        log.warning(result_text)
    else:
        try:
            log.info(f"执行工具: {tool_name}")
            result_text = str(tool.func(**arguments))
        except TypeError:
            # 参数名不匹配（如 LLM 传了 name 但工具只接受 query）——回退用 query 重试
            query_val = next((v for v in arguments.values() if isinstance(v, str)), "")
            log.warning(f"工具 '{tool_name}' 参数不匹配，回退 query 重试: {arguments}")
            try:
                result_text = str(tool.func(query=query_val))
            except Exception as e:
                log.error(f"工具 '{tool_name}' 回退执行也失败: {e}")
                result_text = f"错误：工具执行失败: {e}"
        except Exception as e:
            log.error(f"工具 '{tool_name}' 执行失败: {e}")
            result_text = f"错误：工具执行失败: {e}"

    tool_messages = list(state.get("tool_messages", []))
    tool_messages.append({
        "role": "tool",
        "content": f"调用 {tool_name}({json.dumps(arguments, ensure_ascii=False)}) 结果:\n{result_text}",
    })

    return {"tool_messages": tool_messages}