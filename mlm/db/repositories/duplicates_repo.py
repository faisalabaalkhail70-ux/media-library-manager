import json
from mlm.db.connection import get_connection

class DuplicatesRepository:
    def clear_groups(self) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM duplicate_items")
            conn.execute("DELETE FROM duplicate_groups")

    def create_group(self, match_type: str, confidence: float) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO duplicate_groups (match_type, confidence)
                VALUES (?, ?)
                """,
                (match_type, confidence),
            )
            return int(cur.lastrowid)

    def add_item(self, group_id: int, media_file_id: int, score: float, reason: dict) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO duplicate_items (group_id, media_file_id, score, reason_json)
                VALUES (?, ?, ?, ?)
                """,
                (group_id, media_file_id, score, json.dumps(reason)),
            )

    def fetch_duplicate_rows(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    dg.id AS group_id,
                    dg.match_type,
                    dg.confidence,
                    dg.review_status,
                    mf.id AS media_file_id,
                    mf.file_name,
                    mf.file_path,
                    mf.file_size_bytes,
                    mf.duration_seconds,
                    mf.resolution,
                    mf.video_codec,
                    di.score
                FROM duplicate_groups dg
                JOIN duplicate_items di ON di.group_id = dg.id
                JOIN media_files mf ON mf.id = di.media_file_id
                WHERE mf.removed_at IS NULL
                ORDER BY dg.id, di.score DESC, mf.file_size_bytes DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]