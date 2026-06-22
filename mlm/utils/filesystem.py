"""Filesystem helpers with Windows long-path support.

On Windows, paths longer than 260 characters (MAX_PATH) cause silent
failures in shutil / os functions unless the path is prefixed with
'\\\\?\\' (extended-length path syntax).  The ``to_extended_path`` helper
applies this prefix automatically on Windows; on other platforms it is
a no-op.
"""
import os
import platform
import shutil
from pathlib import Path

_IS_WINDOWS = platform.system() == "Windows"


def to_extended_path(path: str) -> str:
    """Return a Windows extended-length path string on Windows, unchanged elsewhere.

    Prepends ``\\\\?\\`` only when:
    * the OS is Windows,
    * the path is absolute, and
    * it is not already prefixed.
    """
    if not _IS_WINDOWS:
        return path
    abs_path = os.path.abspath(path)
    if abs_path.startswith("\\\\?\\\\" ) or abs_path.startswith("\\\\?\\UNC\\"):
        return abs_path
    if abs_path.startswith("\\\\"):        # UNC network path
        return "\\\\?\\UNC\\" + abs_path[2:]
    return "\\\\?\\" + abs_path


def ensure_parent_dir(path: str) -> None:
    """Create the parent directory of *path* if it does not exist."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def move_file(old_path: str, new_path: str) -> None:
    """Move *old_path* to *new_path*, using extended-length paths on Windows."""
    ensure_parent_dir(new_path)
    shutil.move(to_extended_path(old_path), to_extended_path(new_path))


def safe_exists(path: str) -> bool:
    """Return True if *path* exists, using extended-length path on Windows."""
    return Path(to_extended_path(path)).exists()
