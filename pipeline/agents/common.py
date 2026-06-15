"""Shared helpers cho multi-agent layer.

Khác bản origin: LLM đi qua model_router (OpenRouter/auto provider) thay vì Groq cứng,
để đồng nhất với phần còn lại của pipeline (chat, spike analysis).
"""

from supabase import Client
import hashlib

from env_config import get_supabase_config
from agent.model_router import chat_completion, parse_json_response

_LLM_CACHE = {}


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
    cache_key = hashlib.md5(f"{system_prompt}_{user_message}_{response_format}".encode()).hexdigest()
    if cache_key in _LLM_CACHE:
        return _LLM_CACHE[cache_key]

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    want_json = response_format == "json_object"
    try:
        result = chat_completion(messages, response_json=want_json, temperature=0.1)
        if want_json and result.get("provider") == "mock":
            return ""
        
        content = result.get("content", "") or ""
        if content:
            _LLM_CACHE[cache_key] = content
        return content
    except Exception as exc:  # noqa: BLE001 - agent layer phải bền, không được vỡ pipeline
        print(f"[agents.common] LLM error: {exc}")
        return ""


def log_agent_run(
    run_id: str,
    agent_name: str,
    status: str,
    latency_ms: int = 0,
    output_summary: str = "",
    error_message: str = "",
    input_hash: str = "",
    provider: str = "",
    model: str = "",
    token_usage: dict = None,
    cost_estimate: float = 0.0
):
    """Ghi log execution của agent vào Supabase (Bảng agent_run_logs)."""
    try:
        db = get_db()
        db.table("agent_run_logs").insert({
            "run_id": run_id,
            "agent_name": agent_name,
            "status": status,
            "latency_ms": latency_ms,
            "output_summary": output_summary,
            "error_message": error_message,
            "input_hash": input_hash,
            "provider": provider,
            "model": model,
            "token_usage": token_usage or {},
            "cost_estimate": cost_estimate
        }).execute()
    except Exception as e:
        print(f"[agents.common] Failed to log agent run: {e}")


__all__ = ["get_db", "call_llm", "parse_json_response", "log_agent_run"]
