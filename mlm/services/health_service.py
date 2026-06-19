import os
from pathlib import Path
from mlm.db.connection import get_connection

class HealthService:
    MOVIE_SMALL_BYTES = 50 * 1024 * 1024
    VALID_EXTS = {".mkv", ".mp4", ".avi", ".m4v", ".mov"}

    def list_files_for_health_scan(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, file_path, extension, file_size_bytes
                FROM media_files
                WHERE removed_at IS NULL
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def evaluate_file(self, row: dict) -> tuple[str, str]:
        path = Path(row["file_path"])
        notes = []

        if row["file_size_bytes"] == 0:
            notes.append("0-byte file")

        if row["file_size_bytes"] < self.MOVIE_SMALL_BYTES:
            notes.append("Unusually small media file")

        if row["extension"].lower() not in self.VALID_EXTS:
            notes.append("Unsupported extension")

        srt_path = path.with_suffix(".srt")
        nfo_path = path.with_suffix(".nfo")

        if not srt_path.exists():
            notes.append("Missing subtitle sidecar")
        if not nfo_path.exists():
            notes.append("Missing NFO sidecar")

        if any("0-byte" in n for n in notes):
            status = "error"
        elif notes:
            status = "warning"
        else:
            status = "ok"

        return status, "; ".join(notes)

    def run_health_scan(self) -> dict:
        rows = self.list_files_for_health_scan()
        counts = {"ok": 0, "warning": 0, "error": 0}

        with get_connection() as conn:
            for row in rows:
                status, notes = self.evaluate_file(row)
                conn.execute(
                    """
                    UPDATE media_files
                    SET health_status = ?, health_notes = ?
                    WHERE id = ?
                    """,
                    (status, notes, row["id"]),
                )
                counts[status] += 1

        return counts