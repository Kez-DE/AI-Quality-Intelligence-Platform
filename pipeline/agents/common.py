"""Shared helpers cho multi-agent layer.

Khác bản origin: LLM đi qua model_router (OpenRouter/auto provider) thay vì Groq cứng,
để đồng nhất với phần còn lại của pipeline (chat, spike analysis).
"""

from collections import OrderedDict
from supabase import Client
import hashlib

from env_config import get_supabase_config
from agent.model_router import chat_completion, parse_json_response
from agents.ai_log import log_agent_event

# LRU cache cho LLM response. Dùng OrderedDict + cap để agent-worker (chạy
# dài ngày, 300s/lần) không phình bộ nhớ vô hạn như dict thường.
_LLM_CACHE: "OrderedDict[str, str]" = OrderedDict()
_LLM_CACHE_MAX = 512

# Supabase client là singleton — tránh dựng client mới mỗi lần gọi (18+ chỗ
# gọi log_agent_run trong 1 lượt pipeline). Config tĩnh nên cache an toàn.
_DB_CLIENT: "Client | None" = None


def get_db() -> Client:
    global _DB_CLIENT
    if _DB_CLIENT is not None:
        return _DB_CLIENT
    url, key = get_supabase_config()
    if not url or not key:
        raise ValueError("Supabase URL or Key is missing from environment variables.")
    from supabase import create_client

    _DB_CLIENT = create_client(url, key)
    return _DB_CLIENT


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
        _LLM_CACHE.move_to_end(cache_key)  # đánh dấu vừa dùng (LRU)
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
            _LLM_CACHE.move_to_end(cache_key)
            while len(_LLM_CACHE) > _LLM_CACHE_MAX:
                _LLM_CACHE.popitem(last=False)  # bỏ entry cũ nhất
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
    cost_estimate: float = 0.0,
    team: str = "",
    source: str = "pipeline",
):
    """Ghi log execution của agent vào file ai-log (cục bộ) + Supabase.

    File ai-log ghi trước để debug được ngay cả khi Supabase lỗi/mất mạng.

    team: phòng ban gắn với log (để bóc ai-log theo phòng); source: 'pipeline'|'chat'.
    """
    # 1. File JSONL cục bộ — best-effort, không bao giờ làm vỡ agent
    log_agent_event(
        agent_name=agent_name,
        status=status,
        run_id=run_id,
        latency_ms=latency_ms,
        output_summary=output_summary,
        error_message=error_message,
        provider=provider,
        model=model,
        input_hash=input_hash,
        cost_estimate=cost_estimate,
        team=team,
        source=source,
    )

    # 2. Supabase — nguồn log bền vững
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
