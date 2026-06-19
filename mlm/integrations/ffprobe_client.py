import json
import subprocess
from pathlib import Path

class FFprobeClient:
    def __init__(self, ffprobe_path: str = "ffprobe") -> None:
        self.ffprobe_path = ffprobe_path

    def probe(self, file_path: str) -> dict:
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(completed.stdout or "{}")

    @staticmethod
    def extract_summary(payload: dict) -> dict:
        streams = payload.get("streams", [])
        format_info = payload.get("format", {})

        video = next((s for s in streams if s.get("codec_type") == "video"), {})
        audio = next((s for s in streams if s.get("codec_type") == "audio"), {})

        width = video.get("width")
        height = video.get("height")
        resolution = f"{width}x{height}" if width and height else None

        duration = format_info.get("duration")
        bitrate = format_info.get("bit_rate")

        return {
            "video_codec": video.get("codec_name"),
            "audio_codec": audio.get("codec_name"),
            "width": width,
            "height": height,
            "resolution": resolution,
            "duration_seconds": float(duration) if duration else None,
            "bitrate": int(bitrate) if bitrate else None,
            "container_format": format_info.get("format_name"),
        }