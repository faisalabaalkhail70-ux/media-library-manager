"""FFprobe integration — probes a media file for technical metadata.

Changes in v1.1
---------------
* Replaced blocking subprocess.run() with Popen + communicate(timeout=)
  so the calling thread is never frozen beyond *timeout* seconds.
* Added FileNotFoundError guard before spawning the process.
* Returns empty dict on invalid JSON instead of propagating JSONDecodeError.
"""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from mlm.db.repositories.settings_repo import SettingsRepository

log = logging.getLogger(__name__)


class FFprobeClient:
    """Thin wrapper around the ffprobe CLI."""

    def __init__(self, settings: SettingsRepository | None = None) -> None:
        self._settings = settings or SettingsRepository()

    @property
    def ffprobe_path(self) -> str:
        return self._settings.get("ffprobe_path", "ffprobe") or "ffprobe"

    def probe(self, file_path: str, timeout: int = 30) -> dict:
        """Return ffprobe JSON metadata for *file_path*.

        Raises
        ------
        FileNotFoundError
            If *file_path* does not exist on disk.
        RuntimeError
            If ffprobe does not finish within *timeout* seconds.
        subprocess.CalledProcessError
            If ffprobe exits with a non-zero return code.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Media file not found: {file_path}")

        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
        log.debug("ffprobe probing: %s", file_path)

        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
        ) as proc:
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()  # drain pipes to avoid zombie
                raise RuntimeError(
                    f"ffprobe timed out after {timeout}s on '{file_path}'"
                )

        if proc.returncode != 0:
            log.warning(
                "ffprobe exited %d for '%s': %s",
                proc.returncode, file_path, stderr.strip()
            )
            raise subprocess.CalledProcessError(proc.returncode, cmd)

        try:
            return json.loads(stdout or "{}")
        except json.JSONDecodeError as exc:
            log.error("ffprobe returned invalid JSON for '%s': %s", file_path, exc)
            return {}
