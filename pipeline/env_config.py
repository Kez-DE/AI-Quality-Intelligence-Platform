from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PIPELINE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PIPELINE_DIR.parent

class Settings(BaseSettings):
    # Supabase
    supabase_url: str | None = None
    vite_supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_key: str | None = None
    supabase_publishable_key: str | None = None
    vite_supabase_publishable_key: str | None = None

    # LLM & Models
    llm_provider: str = "auto"
    openrouter_api_key: str = ""
    openrouter_model_name: str = "openrouter/owl-alpha"
    openrouter_site_url: str = "http://localhost:8000"
    openrouter_app_name: str = "AI Quality Intelligence Platform"
    
    openai_api_key: str = ""
    openai_model_name: str = "gpt-4o-mini"
    gemini_api_key: str = ""
    gemini_model_name: str = "gemini-1.5-flash"
    groq_api_key: str = ""
    groq_model_name: str = "llama-3.3-70b-versatile"
    
    # Webhook
    webhook_url: str | None = None
    
    # Live Stream
    live_stream_enabled: bool = False
    live_stream_batch_size: int = 150
    live_stream_interval_seconds: int = 10
    live_stream_loop: bool = False
    live_stream_reset_on_start: bool = False
    
    # Auto Ticket
    auto_ticket_enabled: bool = True
    auto_ticket_every_batches: int = 10
    auto_ticket_max_feedback: int = 1000
    auto_ticket_max_spikes: int = 1
    
    auto_ticket_workflow_enabled: bool = True
    auto_ticket_in_progress_after_seconds: int = 10
    auto_ticket_resolved_after_seconds: int = 30
    
    # Data File
    real_data_file: str | None = None

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()

def get_supabase_config() -> tuple[str | None, str | None]:
    settings = get_settings()
    url = settings.vite_supabase_url or settings.supabase_url
    key = (
        settings.supabase_service_role_key
        or settings.supabase_key
        or settings.supabase_publishable_key
        or settings.vite_supabase_publishable_key
    )
    return url, key

def has_supabase_admin_key() -> bool:
    settings = get_settings()
    return bool(settings.supabase_service_role_key or settings.supabase_key)
