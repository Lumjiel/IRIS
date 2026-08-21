"""
IRIS 结构化错误码
用于 Function Calling 容错和条件边循环终止
"""
from enum import Enum
from typing import Optional, Any


class ErrorCode(str, Enum):
    """IRIS 结构化错误码"""
    DEGRADED_SEARCH = "DEGRADED_SEARCH"          # 搜索降级（Tavily 不可用）
    FALLBACK_LLM = "FALLBACK_LLM"              # LLM 降级（主模型→备模型）
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"  # 工具执行失败
    VALIDATION_FAILED = "VALIDATION_FAILED"        # 输出校验失败
    RATE_LIMIT = "RATE_LIMIT"                      # 限流
    TIMEOUT = "TIMEOUT"                          # 超时
    UNKNOWN = "UNKNOWN"                        # 未知错误


class IrisError(Exception):
    """IRIS 结构化异常"""
    def __init__(self, code: ErrorCode, message: str, details: Optional[dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code.value}] {message}")


# 工厂函数
def degrade_search(reason: str, details: Optional[dict] = None) -> IrisError:
    """创建搜索降级异常"""
    return IrisError(ErrorCode.DEGRADED_SEARCH, reason, details)


def fallback_llm(reason: str, details: Optional[dict] = None) -> IrisError:
    """创建 LLM 降级异常"""
    return IrisError(ErrorCode.FALLBACK_LLM, reason, details)


def tool_execution_failed(tool_name: str, reason: str, details: Optional[dict] = None) -> IrisError:
    """创建工具执行失败异常"""
    return IrisError(ErrorCode.TOOL_EXECUTION_FAILED, f"Tool {tool_name} failed: {reason}", details)


def validation_failed(field: str, reason: str, details: Optional[dict] = None) -> IrisError:
    """创建校验失败异常"""
    return IrisError(ErrorCode.VALIDATION_FAILED, f"Validation failed for {field}: {reason}", details)
