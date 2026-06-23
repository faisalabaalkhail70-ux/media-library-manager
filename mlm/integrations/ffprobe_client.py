"""Thin wrapper around the ffprobe CLI to extract media stream metadata."""
import json
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


class FFprobeClient:
    """Run ffprobe on a media file and parse its JSON output."""

    DEFAULT_TIMEOUT = 30  # seconds before ffprobe is killed

    def __init__(self, ffprobe_path: str = "ffprobe") -> None:
        self.ffprobe_path = ffprobe_path

    def probe(self, file_path: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
        """Return the raw ffprobe JSON payload for *file_path*.

        Uses ``subprocess.Popen`` + ``communicate(timeout=)`` instead of
        ``subprocess.run`` so the caller thread is never blocked indefinitely
        — ffprobe is killed and a ``RuntimeError`` is raised if it exceeds
        *timeout* seconds.

        Raises:
            FileNotFoundError: if ffprobe binary is not on PATH.
            subprocess.CalledProcessError: if ffprobe exits with non-zero status.
            ValueError: if the file does not exist.
            RuntimeError: if ffprobe does not finish within *timeout* seconds.
        """
        if not Path(file_path).exists():
            raise ValueError(f"File not found: {file_path}")

        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]
        log.debug("ffprobe probing: %s", file_path)

        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",   # force UTF-8 instead of system cp1252
            errors="replace",   # replace unmappable bytes instead of crashing
        ) as proc:
            try:
                stdout, _ = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()  # drain pipes to avoid ResourceWarning
                raise RuntimeError(
                    f"ffprobe timed out after {timeout}s on: {file_path}"
                )
            if proc.returncode != 0:
                raise subprocess.CalledProcessError(proc.returncode, cmd)

        return json.loads(stdout or "{}")

    @staticmethod
    def extract_summary(payload: dict) -> dict:
        """Distil the raw ffprobe payload into a flat summary dict."""
        streams = payload.get("streams", [])
        format_info = payload.get("format", {})

        video = next((s for s in streams if s.get("codec_type") == "video"), {})
        audio = next((s for s in streams if s.get("codec_type") == "audio"), {})

        width  = video.get("width")
        height = video.get("height")
        resolution = f"{width}x{height}" if width and height else None

        duration = format_info.get("duration")
        bitrate  = format_info.get("bit_rate")

        return {
            "video_codec":      video.get("codec_name"),
            "audio_codec":      audio.get("codec_name"),
            "width":            width,
            "height":           height,
            "resolution":       resolution,
            "duration_seconds": float(duration) if duration else None,
            "bitrate":          int(bitrate) if bitrate else None,
            "container_format": format_info.get("format_name"),
        }
