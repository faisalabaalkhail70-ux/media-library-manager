"""Repository for duplicate_groups and duplicate_items tables."""
import json
import logging
from mlm.db.connection import get_connection

log = logging.getLogger(__name__)


class DuplicatesRepository:

    def clear_groups(self) -> None:
        """Remove ALL duplicate groups and items."""
        with get_connection() as conn:
            conn.execute("DELETE FROM duplicate_items")
            conn.execute("DELETE FROM duplicate_groups")

    def clear_non_ignored_groups(self) -> None:
        """Remove groups that are NOT marked as ignored (preserves user dismissals)."""
        with get_connection() as conn:
            conn.execute(
                """
                DELETE FROM duplicate_items
                WHERE group_id IN (
                    SELECT id FROM duplicate_groups WHERE review_status != 'ignored'
                )
                """
            )
            conn.execute(
                "DELETE FROM duplicate_groups WHERE review_status != 'ignored'"
            )

    def ignore_group(self, group_id: int) -> None:
        """Mark a group as ignored so it won't reappear on next scan."""
        with get_connection() as conn:
            conn.execute(
                "UPDATE duplicate_groups SET review_status = 'ignored' WHERE id = ?",
                (group_id,),
            )

    def create_group(self, match_type: str, confidence: float) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO duplicate_groups (match_type, confidence, review_status)
                VALUES (?, ?, 'new')
                """,
                (match_type, confidence),
            )
            return int(cur.lastrowid)

    def add_item(self, group_id: int, media_file_id: int,
                 score: float, reason: dict) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO duplicate_items
                    (group_id, media_file_id, score, reason_json)
                VALUES (?, ?, ?, ?)
                """,
                (group_id, media_file_id, score, json.dumps(reason)),
            )

    def fetch_duplicate_rows(self, include_ignored: bool = False) -> list[dict]:
        """Return flat rows for the duplicates table, with score breakdown."""
        status_clause = "" if include_ignored else "AND dg.review_status != 'ignored'"
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    dg.id           AS group_id,
                    dg.match_type,
                    dg.confidence,
                    dg.review_status,
                    di.score,
                    di.reason_json,
                    mf.id           AS file_id,
                    mf.file_name,
                    mf.file_path,
                    mf.file_size_bytes,
                    mf.duration_seconds,
                    mf.resolution,
                    mf.video_codec
                FROM duplicate_groups dg
                JOIN duplicate_items di ON di.group_id = dg.id
                JOIN media_files     mf ON mf.id = di.media_file_id
                WHERE mf.removed_at IS NULL
                {status_clause}
                ORDER BY dg.id, mf.file_size_bytes DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def get_group_ids(self, include_ignored: bool = False) -> list[int]:
        status_clause = "" if include_ignored else "WHERE review_status != 'ignored'"
        with get_connection() as conn:
            rows = conn.execute(
                f"SELECT id FROM duplicate_groups {status_clause} ORDER BY id"
            ).fetchall()
        return [r[0] for r in rows]
