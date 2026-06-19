from mlm.db.connection import get_connection

class ActionsRepository:
    def create_action(
        self,
        *,
        action_type: str,
        media_file_id: int | None,
        old_path: str | None,
        new_path: str | None,
        status: str = "pending",
    ) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO action_ledger (
                    action_type, media_file_id, old_path, new_path, status
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (action_type, media_file_id, old_path, new_path, status),
            )
            return int(cur.lastrowid)

    def mark_done(self, action_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE action_ledger SET status = 'done' WHERE id = ?",
                (action_id,),
            )

    def mark_failed(self, action_id: int, error_message: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE action_ledger
                SET status = 'failed', error_message = ?
                WHERE id = ?
                """,
                (error_message, action_id),
            )

    def mark_undone(self, action_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE action_ledger
                SET status = 'undone', undone_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (action_id,),
            )

    def latest_done_renames(self, limit: int = 100) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, media_file_id, old_path, new_path, created_at
                FROM action_ledger
                WHERE action_type = 'rename' AND status = 'done'
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]