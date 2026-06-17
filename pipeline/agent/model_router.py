import json
import warnings
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Literal, TypedDict

from groq import Groq
from openai import OpenAI

from env_config import get_settings

_s = get_settings()

MessageRole = Literal["system", "user", "assistant"]


class ChatMessage(TypedDict):
    role: MessageRole
    content: str


PIPELINE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = PIPELINE_DIR / "logs"
LOG_FILE = LOG_DIR / "agent.log"

LLM_PROVIDER        = _s.llm_provider
OPENROUTER_API_KEY  = _s.openrouter_api_key
OPENROUTER_MODEL_NAME = _s.openrouter_model_name
OPENAI_API_KEY      = _s.openai_api_key
OPENAI_MODEL_NAME   = _s.openai_model_name
GEMINI_API_KEY      = _s.gemini_api_key
GEMINI_MODEL_NAME   = _s.gemini_model_name
GROQ_API_KEY        = _s.groq_api_key
GROQ_MODEL_NAME     = _s.groq_model_name


def resolve_provider() -> str:
    if LLM_PROVIDER in {"openrouter", "openai", "gemini", "groq", "mock"}:
        return LLM_PROVIDER
    if OPENROUTER_API_KEY:
        return "openrouter"
    if OPENAI_API_KEY:
        return "openai"
    if GEMINI_API_KEY:
        return "gemini"
    if GROQ_API_KEY:
        return "groq"
    return "mock"


# Thứ tự ưu tiên mặc định khi thử failover (provider nào có key sẽ được thử lần lượt).
PROVIDER_PRIORITY = ["openrouter", "openai", "gemini", "groq"]


def resolve_provider_chain() -> list[str]:
    """Trả về danh sách provider sẽ thử lần lượt.

    - Nếu LLM_PROVIDER ép cứng 1 provider hợp lệ (khác 'auto'): chỉ dùng provider đó
      (vẫn thêm 'mock' ở cuối để không bao giờ vỡ).
    - Nếu 'auto' (hoặc rỗng): thử mọi provider CÓ KEY theo thứ tự ưu tiên, rồi 'mock'.

    Nhờ vậy một key chết/hết credit sẽ tự động nhảy sang provider kế tiếp thay vì raise.
    """
    if LLM_PROVIDER in {"openrouter", "openai", "gemini", "groq"}:
        return [LLM_PROVIDER, "mock"]
    if LLM_PROVIDER == "mock":
        return ["mock"]
    chain = [p for p in PROVIDER_PRIORITY if provider_has_key(p)]
    chain.append("mock")
    return chain


def provider_has_key(provider: str) -> bool:
    return {
        "openrouter": bool(OPENROUTER_API_KEY),
        "openai": bool(OPENAI_API_KEY),
        "gemini": bool(GEMINI_API_KEY),
        "groq": bool(GROQ_API_KEY),
        "mock": True,
    }.get(provider, False)


def provider_model(provider: str) -> str:
    return {
        "openrouter": OPENROUTER_MODEL_NAME,
        "openai": OPENAI_MODEL_NAME,
        "gemini": GEMINI_MODEL_NAME,
        "groq": GROQ_MODEL_NAME,
        "mock": "mock",
    }.get(provider, "mock")


def get_agent_status() -> dict:
    provider = resolve_provider()
    return {
        "provider": provider,
        "model": provider_model(provider),
        "has_key": provider_has_key(provider),
        "configured": {
            "openrouter": bool(OPENROUTER_API_KEY),
            "openai": bool(OPENAI_API_KEY),
            "gemini": bool(GEMINI_API_KEY),
            "groq": bool(GROQ_API_KEY),
        },
        "log_file": str(LOG_FILE),
    }


def write_agent_log(event: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": datetime.utcnow().isoformat() + "Z",
        **event,
    }
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def parse_json_response(content: str | None) -> dict:
    if not content:
        raise ValueError("LLM returned empty content")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(content[start : end + 1])


def mock_chat(messages: list[ChatMessage]) -> str:
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    return (
        "Mình đang chạy ở chế độ mock vì chưa có provider key hợp lệ. "
        f"Câu hỏi gần nhất: {last_user[:180]}"
    )


def gemini_messages_to_prompt(messages: list[ChatMessage]) -> str:
    lines = []
    for message in messages:
        role = message["role"]
        content = message["content"]
        lines.append(f"{role.upper()}:\n{content}")
    return "\n\n".join(lines)


def _extract_chat_content(response: object) -> str:
    """Extract content from OpenAI-compatible responses with clear errors."""
    choices = getattr(response, "choices", None)
    if not choices:
        raise ValueError("LLM response has no choices")

    message = getattr(choices[0], "message", None)
    if message is None:
        raise ValueError("LLM response choice has no message")

    content = getattr(message, "content", None)
    if content is None:
        raise ValueError("LLM response message has no content")
        
    usage = getattr(response, "usage", None)
    token_usage = {}
    if usage:
        token_usage = {
            "prompt_tokens": getattr(usage, "prompt_tokens", 0),
            "completion_tokens": getattr(usage, "completion_tokens", 0),
            "total_tokens": getattr(usage, "total_tokens", 0),
        }
        
    return str(content), token_usage


def _call_provider(
    provider: str,
    messages: list[ChatMessage],
    response_json: bool,
    temperature: float,
) -> tuple[str, dict]:
    """Gọi đúng 1 provider, trả về content và usage. Raise nếu provider lỗi (để caller failover)."""
    model_name = provider_model(provider)

    if provider == "mock":
        return mock_chat(messages), {}
    
    import time
    max_retries = 3
    base_delay = 1
    
    for attempt in range(max_retries):
        try:
            if provider == "openrouter":
                client = OpenAI(
                    api_key=OPENROUTER_API_KEY,
                    base_url="https://openrouter.ai/api/v1",
                    default_headers={
                        "HTTP-Referer": _s.openrouter_site_url,
                        "X-Title": _s.openrouter_app_name,
                    },
                )
                kwargs = {"messages": messages, "model": model_name, "temperature": temperature}
                if response_json:
                    kwargs["response_format"] = {"type": "json_object"}
                response = client.chat.completions.create(**kwargs)
                return _extract_chat_content(response)
            if provider == "openai":
                client = OpenAI(api_key=OPENAI_API_KEY)
                kwargs = {"messages": messages, "model": model_name, "temperature": temperature}
                if response_json:
                    kwargs["response_format"] = {"type": "json_object"}
                response = client.chat.completions.create(**kwargs)
                return _extract_chat_content(response)
            if provider == "gemini":
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")
                    import google.generativeai as genai
        
                genai.configure(api_key=GEMINI_API_KEY)
                generation_config = {"temperature": temperature}
                if response_json:
                    generation_config["response_mime_type"] = "application/json"
                model = genai.GenerativeModel(model_name, generation_config=generation_config)
                response = model.generate_content(gemini_messages_to_prompt(messages))
                content = getattr(response, "text", None)
                if content is None:
                    raise ValueError("Gemini response has no text")
                return str(content), {}
            # groq
            client = Groq(api_key=GROQ_API_KEY)
            kwargs = {"messages": messages, "model": model_name, "temperature": temperature}
            if response_json:
                kwargs["response_format"] = {"type": "json_object"}
            response = client.chat.completions.create(**kwargs)
            return _extract_chat_content(response)
            
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str:
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
                    continue
            raise


def chat_completion(
    messages: list[ChatMessage],
    *,
    response_json: bool = False,
    temperature: float = 0.3,
) -> dict:
    """Gọi LLM với failover: thử lần lượt các provider có key trong .env.

    Provider nào lỗi (key chết, hết credit, mạng) thì log lại và thử provider kế tiếp,
    thay vì raise ngay. Chỉ raise khi TẤT CẢ provider thật đều fail (mock luôn ở cuối
    nên thực tế gần như không bao giờ raise — cùng lắm trả lời mock).
    """
    chain = resolve_provider_chain()
    first_user = next((m["content"] for m in messages if m["role"] == "user"), "")
    last_exc: Exception | None = None

    for provider in chain:
        model_name = provider_model(provider)
        started = perf_counter()
        try:
            content, usage = _call_provider(provider, messages, response_json, temperature)
            latency_ms = round((perf_counter() - started) * 1000)
            write_agent_log({
                "event": "chat_completion",
                "provider": provider,
                "model": model_name,
                "ok": True,
                "latency_ms": latency_ms,
                "prompt_preview": first_user[:160],
                "usage": usage,
            })
            return {
                "content": content,
                "provider": provider,
                "model": model_name,
                "latency_ms": latency_ms,
                "usage": usage,
            }
        except Exception as exc:
            last_exc = exc
            latency_ms = round((perf_counter() - started) * 1000)
            write_agent_log({
                "event": "chat_completion",
                "provider": provider,
                "model": model_name,
                "ok": False,
                "latency_ms": latency_ms,
                "error": str(exc)[:500],
                "failover": True,
                "prompt_preview": first_user[:160],
            })
            print(f"[model_router] provider={provider} lỗi, thử provider kế tiếp: {str(exc)[:160]}")
            continue

    # Tất cả provider đều fail (kể cả mock — gần như không xảy ra).
    raise RuntimeError(f"All LLM providers failed. Last error: {last_exc}")
