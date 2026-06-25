from datetime import datetime
from pathlib import Path
from mlm.db.connection import get_connection
from mlm.db.repositories.files_repo import FilesRepository


class ScanService:
    def __init__(self) -> None:
        self.files_repo = FilesRepository()

    def begin_scan_run(self, directory_id: int) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO scan_runs (directory_id, started_at, status)
                VALUES (?, ?, ?)
                """,
                (directory_id, datetime.now().isoformat(timespec="seconds"), "running"),
            )
            return int(cur.lastrowid)

    def finish_scan_run(
        self,
        scan_run_id: int,
        *,
        files_seen: int,
        files_added: int,
        files_updated: int = 0,
        files_removed: int = 0,
        warnings_count: int = 0,
        status: str = "completed",
        error_message: str | None = None,
    ) -> None:
        """Persist the final counters for a completed scan run.

        ``warnings_count`` was previously missing from both the method
        signature and the UPDATE statement, so the schema column was always
        left at 0 regardless of how many warnings the scanner collected
        (issue #11).
        """
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE scan_runs
                SET finished_at    = ?,
                    status         = ?,
                    files_seen     = ?,
                    files_added    = ?,
                    files_updated  = ?,
                    files_removed  = ?,
                    warnings_count = ?,
                    error_message  = ?
                WHERE id = ?
                """,
                (
                    datetime.now().isoformat(timespec="seconds"),
                    status,
                    files_seen,
                    files_added,
                    files_updated,
                    files_removed,
                    warnings_count,
                    error_message,
                    scan_run_id,
                ),
            )

    def save_file_record(self, directory_id: int, file_path: Path) -> None:
        stat = file_path.stat()
        self.files_repo.upsert_file(
            directory_id=directory_id,
            file_path=str(file_path),
            parent_folder=str(file_path.parent),
            file_name=file_path.name,
            extension=file_path.suffix.lower(),
            file_size_bytes=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(
                timespec="seconds"
            ),
        )
