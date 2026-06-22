"""Application-level configuration dataclass."""
from dataclasses import dataclass, field


@dataclass(slots=True)
class AppConfig:
    """Central configuration for the Atlas application."""

    app_name: str = "Atlas"
    organization: str = "Atlas"
    window_width: int = 1480
    window_height: int = 900
    supported_video_exts: tuple[str, ...] = (
        ".mkv", ".mp4", ".avi", ".m4v", ".mov",
        ".wmv", ".ts", ".webm", ".flv", ".vob",
    )
