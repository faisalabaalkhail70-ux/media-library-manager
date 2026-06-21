import os
from pathlib import Path
from mlm.db.connection import get_connection


class HealthService:
    MOVIE_SMALL_BYTES  = 50  * 1024 * 1024   # 50 MB
    EPISODE_SMALL_BYTES = 20 * 1024 * 1024   # 20 MB
    VALID_EXTS = {".mkv", ".mp4", ".avi", ".m4v", ".mov"}

    def list_files_for_health_scan(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, file_path, extension, file_size_bytes, duration_seconds
                FROM media_files
                WHERE removed_at IS NULL
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def evaluate_file(self, row: dict) -> tuple[str, str]:
        notes: list[str] = []
        path = Path(row["file_path"])

        # ── حجم الملف ─────────────────────────────────────────────
        size = row["file_size_bytes"] or 0
        if size == 0:
            notes.append("0-byte file")
        elif size < self.EPISODE_SMALL_BYTES:
            notes.append("Unusually small file (< 20 MB)")
        elif size < self.MOVIE_SMALL_BYTES:
            # قد يكون حلقة مسلسل صغيرة — تحذير خفيف فقط
            notes.append("Small file — may be an episode or short clip")

        # ── الامتداد ──────────────────────────────────────────────
        if row["extension"].lower() not in self.VALID_EXTS:
            notes.append(f"Unsupported extension: {row['extension']}")

        # ── مدة غير موجودة (ffprobe لم يُشغَّل بعد) ──────────────
        if not row.get("duration_seconds"):
            notes.append("Duration not probed yet")

        # ── الملف غير موجود على القرص ─────────────────────────────
        if not path.exists():
            notes.append("File not found on disk")

        # ── تحديد الحالة النهائية ─────────────────────────────────
        if any("0-byte" in n or "not found" in n for n in notes):
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