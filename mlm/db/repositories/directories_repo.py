import logging
from mlm.db.connection import get_connection

log = logging.getLogger(__name__)


class DirectoriesRepository:
    def add_directory(self, path: str, library_type: str = "mixed") -> None:
        with get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO directories (path, library_type) VALUES (?, ?)",
                (path, library_type),
            )

    def list_directories(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, path, library_type, is_enabled, last_scanned_at
                FROM directories ORDER BY path
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def remove_directory(self, directory_id: int) -> None:
        """Remove a directory and NULL-out the FK in media_files so the
        FOREIGN KEY constraint does not fire.
        """
        with get_connection() as conn:
            # Detach files from this directory (keeps file records intact)
            conn.execute(
                "UPDATE media_files SET directory_id = NULL WHERE directory_id = ?",
                (directory_id,),
            )
            # Also detach any scan_runs that reference this directory
            conn.execute(
                "UPDATE scan_runs SET directory_id = NULL WHERE directory_id = ?",
                (directory_id,),
            )
            conn.execute(
                "DELETE FROM directories WHERE id = ?",
                (directory_id,),
            )
        log.info("Removed directory id=%d", directory_id)

    def update_last_scanned(self, directory_id: int, scanned_at: str) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE directories SET last_scanned_at = ? WHERE id = ?",
                (scanned_at, directory_id),
            )
