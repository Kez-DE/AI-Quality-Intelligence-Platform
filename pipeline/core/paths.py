import os
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = PIPELINE_DIR.parent


def resolve_data_dir(pipeline_dir: Path) -> Path:
    """Resolve data/ for both the repository and flattened Docker layout."""
    candidates = (pipeline_dir / "data", pipeline_dir.parent / "data")
    return next((candidate for candidate in candidates if candidate.is_dir()), candidates[0])


DATA_DIR = resolve_data_dir(PIPELINE_DIR)
TAXONOMY_DIR = DATA_DIR / "taxonomy"
DEFAULT_DATA_FILE = str(DATA_DIR / "processed" / "seed_real_clean.json")
