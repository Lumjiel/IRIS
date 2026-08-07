"""
JSON 解析工具 — 从 LLM 输出中稳健地提取 JSON。

LLM 常输出带 Markdown 代码块、前后缀废话的 JSON，这个模块负责剥离噪声。
"""
import json
import re
from typing import Any, Optional


def extract_json(text: str) -> Optional[Any]:
    """从 LLM 输出中提取并解析第一个合法的 JSON 对象/数组。

    - 剥离 ```json ... ``` 代码块
    - 截取第一个 { 到最后一个 }（或 [ 到 ]）
    - 解析失败返回 None
    """
    if not text:
        return None
    text = text.strip()
    text = re.sub(r"```(?:json)?", "", text).strip()

    candidates = [("{", "}"), ("[", "]")]
    for open_ch, close_ch in candidates:
        l = text.find(open_ch)
        r = text.rfind(close_ch)
        if l != -1 and r != -1 and r > l:
            candidate = text[l : r + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    return None


def parse_json_response(text: str, default: Any = None) -> Any:
    """容错解析 LLM JSON 输出，失败返回 default。"""
    parsed = extract_json(text)
    return parsed if parsed is not None else default