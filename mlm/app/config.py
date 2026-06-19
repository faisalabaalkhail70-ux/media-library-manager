from dataclasses import dataclass

@dataclass(slots=True)
class AppConfig:
    app_name: str = "Media Library Manager"
    organization: str = "MLM"
    window_width: int = 1400
    window_height: int = 850
    supported_video_exts: tuple[str, ...] = (".mkv", ".mp4", ".avi", ".m4v", ".mov")