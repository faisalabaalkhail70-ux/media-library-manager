from mlm.db.connection import get_connection
from mlm.db.repositories.settings_repo import SettingsRepository
from mlm.integrations.ffprobe_client import FFprobeClient

class ProbeService:
    def __init__(self) -> None:
        settings = SettingsRepository()
        ffprobe_path = settings.get("ffprobe_path", "ffprobe")
        self.client = FFprobeClient(ffprobe_path=ffprobe_path)

    def list_files_needing_probe(self, limit: int = 300) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, file_path
                FROM media_files
                WHERE removed_at IS NULL
                  AND (resolution IS NULL OR video_codec IS NULL OR duration_seconds IS NULL)
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
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