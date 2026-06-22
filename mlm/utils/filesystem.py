"""Filesystem utilities used across the application."""
import os
import platform
import shutil


def safe_exists(path: str) -> bool:
    """Check if *path* exists.

    On case-insensitive file-systems (Windows, macOS HFS+) this performs a
    case-insensitive directory listing so that a rename from
    ``Game.of.Thrones.mkv`` → ``Game of Thrones.mkv`` on a filesystem that
    already has ``game of thrones.mkv`` is correctly detected as a conflict
    instead of silently overwriting the file.
    """
    if not path:
        return False
    if platform.system() in ("Windows", "Darwin"):
        folder = os.path.dirname(path) or "."
        name   = os.path.basename(path).lower()
        try:
            return any(f.lower() == name for f in os.listdir(folder))
        except OSError:
            return os.path.exists(path)
    return os.path.exists(path)


def move_file(src: str, dst: str) -> None:
    """Move *src* to *dst*, creating parent directories as needed."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)
