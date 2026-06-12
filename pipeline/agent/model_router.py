import json
import os
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Literal, TypedDict

import google.generativeai as genai
from groq import Groq
from openai import OpenAI

from env_config import load_project_env

load_project_env()

MessageRole = Literal["system", "user", "assistant"]


class ChatMessage(TypedDict):
    role: MessageRole
    content: str


PIPELINE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = PIPELINE_DIR / "logs"
LOG_FILE = LOG_DIR / "agent.log"

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").strip().lower()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL_NAME = os.getenv("OPENROUTER_MODEL_NAME", "openrouter/owl-alpha")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")


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


def chat_completion(
    messages: list[ChatMessage],
    *,
    response_json: bool = False,
    temperature: float = 0.3,
) -> dict:
    provider = resolve_provider()
    if not provider_has_key(provider):
        provider = "mock"
    model_name = provider_model(provider)
    started = perf_counter()
    first_user = next((m["content"] for m in messages if m["role"] == "user"), "")

    try:
        if provider == "mock":
            content = mock_chat(messages)
        elif provider == "openrouter":
            client = OpenAI(
                api_key=OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost:8000"),
                    "X-Title": os.getenv("OPENROUTER_APP_NAME", "AI Quality Intelligence Platform"),
                },
            )
            kwargs = {
                "messages": messages,
                "model": model_name,
                "temperature": temperature,
            }
            if response_json:
                kwargs["response_format"] = {"type": "json_object"}
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
        elif provider == "openai":
            client = OpenAI(api_key=OPENAI_API_KEY)
            kwargs = {
                "messages": messages,
                "model": model_name,
                "temperature": temperature,
            }
            if response_json:
                kwargs["response_format"] = {"type": "json_object"}
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
        elif provider == "gemini":
            genai.configure(api_key=GEMINI_API_KEY)
            generation_config = {"temperature": temperature}
            if response_json:
                generation_config["response_mime_type"] = "application/json"
            model = genai.GenerativeModel(model_name, generation_config=generation_config)
            response = model.generate_content(gemini_messages_to_prompt(messages))
            content = response.text
        else:
            client = Groq(api_key=GROQ_API_KEY)
            kwargs = {
                "messages": messages,
                "model": model_name,
                "temperature": temperature,
            }
            if response_json:
                kwargs["response_format"] = {"type": "json_object"}
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""

        latency_ms = round((perf_counter() - started) * 1000)
        write_agent_log({
            "event": "chat_completion",
            "provider": provider,
            "model": model_name,
            "ok": True,
            "latency_ms": latency_ms,
            "prompt_preview": first_user[:160],
        })
        return {
            "content": content,
            "provider": provider,
            "model": model_name,
            "latency_ms": latency_ms,
        }
    except Exception as exc:
        latency_ms = round((perf_counter() - started) * 1000)
        write_agent_log({
            "event": "chat_completion",
            "provider": provider,
            "model": model_name,
            "ok": False,
            "latency_ms": latency_ms,
            "error": str(exc)[:500],
            "prompt_preview": first_user[:160],
        })
        raise
