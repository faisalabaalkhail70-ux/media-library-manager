"""Resolve application directory paths and ensure they exist."""
from pathlib import Path

APP_NAME = "Atlas"

ROOT_DIR   = Path(__file__).resolve().parents[2]
DATA_DIR   = ROOT_DIR / "data"
DB_PATH    = DATA_DIR / "app.db"
LOG_DIR    = DATA_DIR / "logs"
EXPORT_DIR = DATA_DIR / "exports"
POSTER_DIR = DATA_DIR / "posters"    # cached poster thumbnails


def ensure_app_dirs() -> None:
    """Create required data directories if they do not exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    POSTER_DIR.mkdir(parents=True, exist_ok=True)
