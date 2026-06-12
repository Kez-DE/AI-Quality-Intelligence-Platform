import os
from pathlib import Path

from dotenv import load_dotenv


PIPELINE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = PIPELINE_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent


def load_project_env() -> None:
    load_dotenv(PROJECT_ROOT / ".env", override=False)


def get_supabase_config() -> tuple[str | None, str | None]:
    load_project_env()
    url = os.getenv("VITE_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_PUBLISHABLE_KEY")
        or os.getenv("VITE_SUPABASE_PUBLISHABLE_KEY")
    )
    return url, key


def has_supabase_admin_key() -> bool:
    load_project_env()
    return bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY"))
