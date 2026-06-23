"""Health scan service — checks every tracked file is still accessible.

Changes in v1.1
---------------
* N+1 DB writes eliminated: individual UPDATE statements inside the loop
  replaced with a single executemany call after all evaluations complete.
* Extension list imported from AppConfig (single source of truth) instead
  of being duplicated here.
"""
from __future__ import annotations

import logging
from pathlib import Path

from mlm.app.config import AppConfig
from mlm.db.connection import get_connection

log = logging.getLogger(__name__)

_cfg = AppConfig()
VALID_EXTS: frozenset[str] = frozenset(_cfg.supported_video_exts)


class HealthService:
    """Evaluates the on-disk health of every non-removed media file."""

    def list_files_for_health_scan(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, file_path, extension, file_size_bytes
                FROM   media_files
                WHERE  removed_at IS NULL
                ORDER  BY id
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def evaluate_file(self, row: dict) -> tuple[str, str]:
        """Return (status, notes) for a single file row."""
        path = Path(row["file_path"])
        if not path.exists():
            return "error", "File not found on disk"
        if row["extension"].lower() not in VALID_EXTS:
            return "warning", f"Unsupported extension: {row['extension']}"
        try:
            actual_size = path.stat().st_size
        except OSError as exc:
            return "error", f"Cannot stat file: {exc}"
        if actual_size == 0:
            return "error", "File is empty (0 bytes)"
        if row["file_size_bytes"] and actual_size != row["file_size_bytes"]:
            return (
                "warning",
                f"Size mismatch: DB={row['file_size_bytes']} bytes, disk={actual_size} bytes",
            )
        return "ok", ""

    def run_health_scan(self) -> dict:
        """Scan all tracked files and persist results in a single batch write."""
        rows   = self.list_files_for_health_scan()
        counts: dict[str, int] = {"ok": 0, "warning": 0, "error": 0}
        updates: list[tuple[str, str, int]] = []

        for row in rows:
            status, notes = self.evaluate_file(row)
            updates.append((status, notes, row["id"]))
            counts[status] = counts.get(status, 0) + 1
            log.debug("Health %s: %s", status, row["file_path"])

        with get_connection() as conn:
            conn.executemany(
                "UPDATE media_files SET health_status = ?, health_notes = ? WHERE id = ?",
                updates,
            )

        log.info("Health scan complete: %s", counts)
        return counts
