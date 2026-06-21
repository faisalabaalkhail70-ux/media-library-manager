from dataclasses import dataclass

@dataclass(slots=True)
class AppConfig:
    app_name: str = "Atlas"
    organization: str = "Atlas"
    window_width: int = 1480
    window_height: int = 900
    supported_video_exts: tuple[str, ...] = (".mkv", ".mp4", ".avi", ".m4v", ".mov")