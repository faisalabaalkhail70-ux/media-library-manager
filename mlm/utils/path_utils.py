from pathlib import Path

def normalize_path(path: str) -> str:
    return str(Path(path))

def windows_long_path(path: str) -> str:
    p = str(Path(path).resolve())
    if p.startswith("\\\\?\\"):
        return p
    if p.startswith("\\\\"):
        return "\\\\?\\UNC\\" + p.lstrip("\\")
    return "\\\\?\\" + p