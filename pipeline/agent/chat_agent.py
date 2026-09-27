import json
import os
import re
import sys

# Ensure pipeline dir is in sys.path for clean.py
PIPELINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PIPELINE_DIR not in sys.path:
    sys.path.append(PIPELINE_DIR)

from clean import mask_pii
from .model_router import chat_completion, ChatMessage
from .chat_tools import TOOLS_DEFINITIONS, execute_tool


def _fill_contact_placeholders(text: str) -> str:
    """Lưới an toàn: nếu model tự che kênh liên hệ công khai bằng ký hiệu thay thế
    ([EMAIL], [SĐT], [PHONE], [HOTLINE]...), thay lại bằng giá trị công khai thật."""
    if not text:
        return text
    text = re.sub(r"\[\s*e-?mail\s*\]", "support.vn@greensm.com", text, flags=re.IGNORECASE)
    text = re.sub(r"\[\s*(?:sđt|sdt|phone|hotline|số điện thoại)\s*\]", "1555", text, flags=re.IGNORECASE)
    return text


def run_chat_agent(
    messages: list[ChatMessage],
    temperature: float = 0.3,
    max_loops: int = 5,
    scope_team: str | None = None,
    tools_override: list | None = None,
    execute_fn=None,
) -> dict:
    """Chạy vòng lặp ReAct agent để LLM tự gọi công cụ (nếu cần) trước khi trả lời.

    scope_team: phòng ban của ops user. Nếu set, mọi tool bị ép lọc về đúng phòng
    này (chống rò rỉ dữ liệu chéo phòng). None = admin/toàn hệ thống.

    tools_override: thay thế TOOLS_DEFINITIONS mặc định bằng danh sách tool tuỳ chỉnh
    (dùng cho tầng công khai public_only: chỉ truyền PUBLIC_TOOLS_DEFINITIONS).

    execute_fn: hàm thực thi tool (name, args) -> str tuỳ chỉnh. Nếu không truyền,
    dùng execute_tool mặc định (dành cho ops/admin).
    """
    active_tools = tools_override if tools_override is not None else TOOLS_DEFINITIONS
    collected_sources: list = []
    # Ghi lại tool đã THỰC SỰ chạy. Không có vết này thì không thể chứng minh
    # phạm vi bị ép ở tầng thực thi công cụ — chỉ suy đoán từ câu trả lời.
    tools_used: list[dict] = []

    def _execute(name: str, args: dict) -> str:
        tools_used.append({"name": name, "scope_team": scope_team})
        if execute_fn is not None:
            return execute_fn(name, args)
        return execute_tool(name, args, scope_team=scope_team, sources_out=collected_sources)

    # Lọc PII từ input messages
    current_messages = []
    for m in messages:
        m_copy = dict(m)
        if m_copy.get("role") in ("user", "assistant") and m_copy.get("content"):
            m_copy["content"] = mask_pii(m_copy["content"])
        current_messages.append(m_copy)
    
    for loop_idx in range(max_loops):
        try:
            # Call model with tools
            result = chat_completion(
                current_messages,
                temperature=temperature,
                tools=active_tools
            )
        except ValueError as e:
            # Fallback nếu provider (vd: Gemini) không hỗ trợ tools
            if "not supported" in str(e).lower():
                # Bỏ tools đi và thử lại
                result = chat_completion(
                    current_messages,
                    temperature=temperature
                )
            else:
                raise e
        
        msg_dict = result.get("message", {})
        current_messages.append(msg_dict)
        
        tool_calls = msg_dict.get("tool_calls")
        if not tool_calls:
            # LLM không gọi tool nào, trả về kết quả ngay (trả lời text)
            # Lọc PII từ kết quả trả về trước khi đưa ra ngoài
            if result.get("content"):
                result["content"] = _fill_contact_placeholders(mask_pii(result["content"]))
            if "message" in result and result["message"].get("content"):
                result["message"]["content"] = _fill_contact_placeholders(mask_pii(result["message"]["content"]))
            if collected_sources:
                result["sources"] = collected_sources
            result["tools_used"] = tools_used
            return result
            
        # Có tool calls -> thực thi các tools
        for tc in tool_calls:
            tc_id = tc.get("id")
            func = tc.get("function", {})
            name = func.get("name")
            args_str = func.get("arguments", "{}")
            
            try:
                args = json.loads(args_str) if args_str else {}
            except Exception:
                args = {}
                
            # Thực thi tool (ops dùng execute_tool, tầng công khai dùng execute_fn)
            tool_result = _execute(name, args)
            
            # Lọc PII từ tool context
            safe_tool_result = mask_pii(str(tool_result))
            
            # Gắn kết quả của hàm vào context để gửi lên LLM ở vòng lặp tiếp theo
            tool_msg = {
                "role": "tool",
                "content": safe_tool_result,
                "tool_call_id": tc_id,
                "name": name
            }
            current_messages.append(tool_msg)
            
    # Nếu vượt quá số vòng lặp tối đa
    return {
        "content": "Tôi đã thử phân tích dữ liệu nhưng mất quá nhiều bước. Vui lòng yêu cầu ngắn gọn hoặc cụ thể hơn.",
        "provider": "system",
        "model": "agent_loop",
        "sources": collected_sources,
        "tools_used": tools_used,
    }

