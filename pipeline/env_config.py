"""Centralised configuration — powered by pydantic-settings.

All environment variables live here. Everywhere else in the pipeline
imports `get_settings()` instead of calling os.getenv() directly.

Usage:
    from env_config import get_settings
    s = get_settings()
    url = s.effective_supabase_url
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# pipeline/ sits directly under the repository root in this layout.
PIPELINE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PIPELINE_DIR.parent

# Load .env early so pydantic-settings can pick up the values.
# override=False means Railway / Docker injected vars take precedence.
load_dotenv(PROJECT_ROOT / ".env", override=False)


class Settings(BaseSettings):
    """All runtime configuration for the pipeline.

    Railway injects these as env vars; locally they come from .env.
    Pydantic validates types and gives clear errors on misconfiguration.
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------
    # Supabase
    # ------------------------------------------------------------------
    vite_supabase_url: str = Field(default="", alias="VITE_SUPABASE_URL")
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(default="", alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_key: str = Field(default="", alias="SUPABASE_KEY")
    supabase_publishable_key: str = Field(default="", alias="SUPABASE_PUBLISHABLE_KEY")
    vite_supabase_publishable_key: str = Field(default="", alias="VITE_SUPABASE_PUBLISHABLE_KEY")

    @property
    def effective_supabase_url(self) -> str:
        return self.vite_supabase_url or self.supabase_url

    @property
    def effective_supabase_key(self) -> str:
        return (
            self.supabase_service_role_key
            or self.supabase_key
            or self.supabase_publishable_key
            or self.vite_supabase_publishable_key
        )

    @property
    def has_supabase_admin_key(self) -> bool:
        return bool(self.supabase_service_role_key or self.supabase_key)

    # ------------------------------------------------------------------
    # LLM providers
    # ------------------------------------------------------------------
    llm_provider: str = Field(default="auto", alias="LLM_PROVIDER")

    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model_name: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL_NAME")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model_name: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL_NAME")

    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model_name: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL_NAME")

    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_model_name: str = Field(default="openrouter/owl-alpha", alias="OPENROUTER_MODEL_NAME")
    openrouter_site_url: str = Field(default="http://localhost:8000", alias="OPENROUTER_SITE_URL")
    openrouter_app_name: str = Field(default="AI Quality Intelligence Platform", alias="OPENROUTER_APP_NAME")

    # ------------------------------------------------------------------
    # Webhook notifications
    # ------------------------------------------------------------------
    webhook_url: str = Field(default="", alias="WEBHOOK_URL")

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------
    real_data_file: str = Field(default="", alias="REAL_DATA_FILE")

    # ------------------------------------------------------------------
    # Worker intervals
    # ------------------------------------------------------------------
    worker_ticket_workflow_interval_seconds: int = Field(default=15, alias="WORKER_TICKET_WORKFLOW_INTERVAL_SECONDS")
    worker_ml_batch_size: int = Field(default=50, alias="WORKER_ML_BATCH_SIZE")
    worker_ml_interval_seconds: int = Field(default=60, alias="WORKER_ML_INTERVAL_SECONDS")
    worker_agent_interval_seconds: int = Field(default=300, alias="WORKER_AGENT_INTERVAL_SECONDS")
    worker_agent_hours: int = Field(default=24, alias="WORKER_AGENT_HOURS")
    worker_agent_enabled: bool = Field(default=True, alias="WORKER_AGENT_ENABLED")

    # ------------------------------------------------------------------
    # Live stream
    # ------------------------------------------------------------------
    live_stream_enabled: bool = Field(default=False, alias="LIVE_STREAM_ENABLED")
    live_stream_batch_size: int = Field(default=150, alias="LIVE_STREAM_BATCH_SIZE")
    live_stream_interval_seconds: int = Field(default=10, alias="LIVE_STREAM_INTERVAL_SECONDS")
    live_stream_loop: bool = Field(default=False, alias="LIVE_STREAM_LOOP")
    live_stream_reset_on_start: bool = Field(default=False, alias="LIVE_STREAM_RESET_ON_START")
    auto_ticket_enabled: bool = Field(default=True, alias="AUTO_TICKET_ENABLED")
    auto_ticket_every_batches: int = Field(default=2, alias="AUTO_TICKET_EVERY_BATCHES")
    auto_ticket_max_spikes: int = Field(default=6, alias="AUTO_TICKET_MAX_SPIKES")
    ticket_critical_threshold: int = Field(default=1, alias="TICKET_CRITICAL_THRESHOLD")
    ticket_high_risk_threshold: int = Field(default=3, alias="TICKET_HIGH_RISK_THRESHOLD")
    ticket_volume_spike_threshold: int = Field(default=10, alias="TICKET_VOLUME_SPIKE_THRESHOLD")
    ticket_marketing_spike_threshold: int = Field(default=5, alias="TICKET_MARKETING_SPIKE_THRESHOLD")
    ticket_alert_cooldown_minutes: int = Field(default=60, alias="TICKET_ALERT_COOLDOWN_MINUTES")
    auto_ticket_workflow_enabled: bool = Field(default=True, alias="AUTO_TICKET_WORKFLOW_ENABLED")
    auto_ticket_in_progress_after_seconds: int = Field(default=10, alias="AUTO_TICKET_IN_PROGRESS_AFTER_SECONDS")
    auto_ticket_resolved_after_seconds: int = Field(default=30, alias="AUTO_TICKET_RESOLVED_AFTER_SECONDS")

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------
    rate_limit_chat_guest: int = Field(default=20, alias="RATE_LIMIT_CHAT_GUEST")
    rate_limit_chat_staff: int = Field(default=100, alias="RATE_LIMIT_CHAT_STAFF")
    rate_limit_feedback_guest: int = Field(default=10, alias="RATE_LIMIT_FEEDBACK_GUEST")

    @field_validator("llm_provider", mode="before")
    @classmethod
    def normalise_provider(cls, v: str) -> str:
        return str(v).strip().lower()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance (cached after first call)."""
    return Settings()


# ---------------------------------------------------------------------------
# Backwards-compatible helpers used by existing code
# ---------------------------------------------------------------------------

def load_project_env() -> None:
    """Legacy no-op — dotenv is loaded at module import time."""


def get_supabase_config() -> tuple[str | None, str | None]:
    """Legacy helper — returns (url, key) tuple."""
    s = get_settings()
    return s.effective_supabase_url or None, s.effective_supabase_key or None


def has_supabase_admin_key() -> bool:
    """Legacy helper."""
    return get_settings().has_supabase_admin_key
