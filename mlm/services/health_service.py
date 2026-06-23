"""Evaluate the health of media files and persist the result to the DB."""
import logging
from pathlib import Path

from mlm.app.config import AppConfig
from mlm.db.connection import get_connection

log = logging.getLogger(__name__)

# Single source of truth: derive valid extensions from AppConfig.
_cfg = AppConfig()
VALID_EXTS: frozenset[str] = frozenset(_cfg.supported_video_exts)


class HealthService:
    """Scan every known media file and assign a health_status label."""

    MOVIE_SMALL_BYTES   = 50 * 1024 * 1024   # 50 MB
    EPISODE_SMALL_BYTES = 20 * 1024 * 1024   # 20 MB

    def list_files_for_health_scan(self) -> list[dict]:
        """Return all active (non-removed) media file rows."""
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
        """Return *(status, notes)* for a single file row.

        Status is one of ``'ok'``, ``'warning'``, or ``'error'``.
        """
        notes: list[str] = []
        path = Path(row["file_path"])

        size = row["file_size_bytes"] or 0
        if size == 0:
            notes.append("0-byte file")
        elif size < self.EPISODE_SMALL_BYTES:
            notes.append("Unusually small file (< 20 MB)")
        elif size < self.MOVIE_SMALL_BYTES:
            notes.append("Small file \u2014 may be an episode or short clip")

        if row["extension"].lower() not in VALID_EXTS:
            notes.append(f"Unsupported extension: {row['extension']}")

        if not row.get("duration_seconds"):
            notes.append("Duration not probed yet")

        if not path.exists():
            notes.append("File not found on disk")

        if any(kw in n for n in notes for kw in ("0-byte", "not found")):
            status = "error"
        elif notes:
            status = "warning"
        else:
            status = "ok"

        return status, "; ".join(notes)

    def run_health_scan(self) -> dict:
        """Evaluate every file and write results back to the DB.

        All updates are batched into a single ``executemany`` call to
        avoid the N+1 write pattern that previously caused 10,000+
        individual UPDATE statements on large libraries.

        Returns:
            Counts dict: ``{"ok": n, "warning": n, "error": n}``.
        """
        rows = self.list_files_for_health_scan()
        counts: dict[str, int] = {"ok": 0, "warning": 0, "error": 0}
        updates: list[tuple[str, str, int]] = []

        for row in rows:
            status, notes = self.evaluate_file(row)
            updates.append((status, notes, row["id"]))
            counts[status] += 1
            log.debug("Health %s: %s", status, row["file_path"])

        with get_connection() as conn:
            conn.executemany(
                """
                UPDATE media_files
                SET health_status = ?, health_notes = ?
                WHERE id = ?
                """,
                updates,
            )

        log.info("Health scan complete: %s", counts)
        return counts
