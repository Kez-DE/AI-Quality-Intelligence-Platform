"""Shared helpers cho multi-agent layer.

Khác bản origin: LLM đi qua model_router (OpenRouter/auto provider) thay vì Groq cứng,
để đồng nhất với phần còn lại của pipeline (chat, spike analysis).
"""

from supabase import Client

from env_config import get_supabase_config
from agent.model_router import chat_completion, parse_json_response


def get_db() -> Client:
    url, key = get_supabase_config()
    if not url or not key:
        raise ValueError("Supabase URL or Key is missing from environment variables.")
    from supabase import create_client

    return create_client(url, key)


def call_llm(
    system_prompt: str,
    user_message: str,
    response_format: str = "text",
) -> str:
    """Gọi LLM qua model_router (provider auto: OpenRouter -> OpenAI -> ... -> mock).

    Trả về string content. Khi mock/lỗi, model_router tự fallback nên caller chỉ
    cần xử lý trường hợp chuỗi rỗng hoặc JSON parse fail.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    want_json = response_format == "json_object"
    try:
        result = chat_completion(messages, response_json=want_json, temperature=0.1)
        return result.get("content", "") or ""
    except Exception as exc:  # noqa: BLE001 - agent layer phải bền, không được vỡ pipeline
        print(f"[agents.common] LLM error: {exc}")
        return ""


__all__ = ["get_db", "call_llm", "parse_json_response"]
