"""Run ffprobe on files that are missing resolution/codec/duration data."""
import logging

from mlm.db.connection import get_connection
from mlm.db.repositories.settings_repo import SettingsRepository
from mlm.integrations.ffprobe_client import FFprobeClient

log = logging.getLogger(__name__)


class ProbeService:
    def __init__(self) -> None:
        settings = SettingsRepository()
        ffprobe_path = settings.get("ffprobe_path", "ffprobe")
        self.client = FFprobeClient(ffprobe_path=ffprobe_path)

    def list_files_needing_probe(self, limit: int = 0) -> list[dict]:
        """Return files that still need probing.  limit=0 means all.

        Previously duplicated the full SQL string inside an if/else to
        conditionally append LIMIT.  Now builds the query once and appends
        the clause only when limit > 0, eliminating the copy-paste.
        """
        sql = """
            SELECT id, file_path
            FROM media_files
            WHERE removed_at IS NULL
              AND (resolution IS NULL OR video_codec IS NULL OR duration_seconds IS NULL)
            ORDER BY id DESC
        """
        params: tuple = ()
        if limit > 0:
            sql += " LIMIT ?"
            params = (limit,)

        with get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def probe_file(self, media_file_id: int, file_path: str) -> dict:
        raw = self.client.probe(file_path)
        summary = self.client.extract_summary(raw)

        with get_connection() as conn:
            conn.execute(
                """
                UPDATE media_files
                SET video_codec = ?,
                    audio_codec = ?,
                    width = ?,
                    height = ?,
                    resolution = ?,
                    duration_seconds = ?,
                    bitrate = ?,
                    container_format = ?
                WHERE id = ?
                """,
                (
                    summary["video_codec"],
                    summary["audio_codec"],
                    summary["width"],
                    summary["height"],
                    summary["resolution"],
                    summary["duration_seconds"],
                    summary["bitrate"],
                    summary["container_format"],
                    media_file_id,
                ),
            )

        return summary

    def mark_probe_error(self, media_file_id: int, reason: str) -> None:
        """Stamp a file with health_status='error' so it won't be retried silently."""
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE media_files
                SET health_status = 'error',
                    health_notes  = ?
                WHERE id = ?
                """,
                (reason, media_file_id),
            )
