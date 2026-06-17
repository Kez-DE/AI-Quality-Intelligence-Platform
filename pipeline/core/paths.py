import os

PIPELINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(PIPELINE_DIR, ".."))
DEFAULT_DATA_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "processed",
    "seed_real_clean.json",
)
