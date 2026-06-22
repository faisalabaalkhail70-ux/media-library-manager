"""QThread worker that computes partial or full MD5 hashes for media files."""
import logging
from PySide6.QtCore import QThread, Signal
from mlm.db.repositories.files_repo import FilesRepository
from mlm.utils.hashing import partial_md5, full_md5

log = logging.getLogger(__name__)

# Safe whitelist mapping mode → column name, preventing SQL injection.
_MODE_TO_COLUMN: dict[str, str] = {
    "partial": "partial_hash",
    "full": "full_hash",
}


class HashWorker(QThread):
    """Compute partial or full file hashes in a background thread.

    Args:
        mode: ``"partial"`` (fast, first 10 MB) or ``"full"`` (entire file).
    """

    progress = Signal(int, int)  # (done, total)
    finished = Signal(int)       # files_hashed
    failed = Signal(str)

    def __init__(self, mode: str = "partial") -> None:
        super().__init__()
        if mode not in _MODE_TO_COLUMN:
            raise ValueError(f"Invalid hash mode '{mode}'. Must be one of {list(_MODE_TO_COLUMN)}.")
        self.mode = mode
        self.repo = FilesRepository()
        self._running = True

    def stop(self) -> None:
        """Signal the worker to stop after the current file."""
        self._running = False

    def run(self) -> None:
        """Hash all unhashed files and emit progress signals."""
        try:
            files = self._get_unhashed_files()
            total = len(files)
            done = 0

            for row in files:
                if not self._running:
                    break

                path = row["file_path"]
                try:
                    if self.mode == "full":
                        h = full_md5(path)
                        self.repo.save_hashes(file_path=path, full_hash=h)
                    else:
                        h = partial_md5(path)
                        self.repo.save_hashes(file_path=path, partial_hash=h)
                except OSError as exc:
                    log.warning("Skipping unreadable file %s: %s", path, exc)
                except Exception as exc:
                    log.error("Unexpected error hashing %s: %s", path, exc, exc_info=True)

                done += 1
                if done % 5 == 0:
                    self.progress.emit(done, total)

            self.finished.emit(done)

        except Exception as exc:
            log.exception("HashWorker crashed")
            self.failed.emit(str(exc))

    def _get_unhashed_files(self) -> list[dict]:
        """Return all files that have not yet been hashed in the selected mode."""
        from mlm.db.connection import get_connection
        col = _MODE_TO_COLUMN[self.mode]  # safe: validated in __init__
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT id, file_path, file_size_bytes
                FROM media_files
                WHERE removed_at IS NULL
                  AND {col} IS NULL
                ORDER BY file_size_bytes DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]
