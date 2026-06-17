import os
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = PIPELINE_DIR.parent

# Trong Docker, Dockerfile copy data/ vào /app/data/ và pipeline/ vào /app/
# nên PIPELINE_DIR = /app, PROJECT_ROOT = / (sai).
# Cần tìm data/ relative to PIPELINE_DIR trước, fallback về PROJECT_ROOT.
_data_candidate = PIPELINE_DIR / "data" / "processed" / "seed_real_clean.json"
_data_fallback   = PROJECT_ROOT / "data" / "processed" / "seed_real_clean.json"

DEFAULT_DATA_FILE = str(
    _data_candidate if _data_candidate.exists() else _data_fallback
)
