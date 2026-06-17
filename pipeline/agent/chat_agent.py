import json
from .model_router import chat_completion, ChatMessage
from .chat_tools import TOOLS_DEFINITIONS, execute_tool

def run_chat_agent(messages: list[ChatMessage], temperature: float = 0.3, max_loops: int = 5) -> dict:
    """Chạy vòng lặp ReAct agent để LLM tự gọi công cụ (nếu cần) trước khi trả lời."""
    current_messages = list(messages)
    
    for loop_idx in range(max_loops):
        try:
            # Call model with tools
            result = chat_completion(
                current_messages,
                temperature=temperature,
                tools=TOOLS_DEFINITIONS
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
                
            # Thực thi hàm truy vấn dữ liệu thực tế
            tool_result = execute_tool(name, args)
            
            # Gắn kết quả của hàm vào context để gửi lên LLM ở vòng lặp tiếp theo
            tool_msg = {
                "role": "tool",
                "content": str(tool_result),
                "tool_call_id": tc_id,
                "name": name
            }
            current_messages.append(tool_msg)
            
    # Nếu vượt quá số vòng lặp tối đa
    return {
        "content": "Tôi đã thử phân tích dữ liệu nhưng mất quá nhiều bước. Vui lòng yêu cầu ngắn gọn hoặc cụ thể hơn.",
        "provider": "system",
        "model": "agent_loop"
    }
