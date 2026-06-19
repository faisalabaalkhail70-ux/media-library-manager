import os
from mlm.db.connection import get_connection
from mlm.db.repositories.actions_repo import ActionsRepository
from mlm.utils.filesystem import move_file, safe_exists

class UndoService:
    def __init__(self) -> None:
        self.actions_repo = ActionsRepository()

    def undo_latest_renames(self, limit: int = 20) -> dict:
        rows = self.actions_repo.latest_done_renames(limit=limit)
        undone = 0
        failed = 0

        with get_connection() as conn:
            for row in rows:
                old_path = row["old_path"]
                new_path = row["new_path"]

                try:
                    if not new_path or not old_path:
                        failed += 1
                        continue
                    if not safe_exists(new_path):
                        failed += 1
                        continue
                    if safe_exists(old_path):
                        failed += 1
                        continue

                    move_file(new_path, old_path)
                    conn.execute(
                        """
                        UPDATE media_files
                        SET file_path = ?, file_name = ?, parent_folder = ?
                        WHERE id = ?
                        """,
                        (
                            old_path,
                            os.path.basename(old_path),
                            os.path.dirname(old_path),
                            row["media_file_id"],
                        ),
                    )
                    self.actions_repo.mark_undone(row["id"])
                    undone += 1
                except Exception:
                    failed += 1

        return {"undone": undone, "failed": failed}