import shutil
from pathlib import Path

def ensure_parent_dir(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)

def move_file(old_path: str, new_path: str) -> None:
    ensure_parent_dir(new_path)
    shutil.move(old_path, new_path)

def safe_exists(path: str) -> bool:
    return Path(path).exists()