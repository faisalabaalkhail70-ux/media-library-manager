"""QThread worker that computes partial or full BLAKE2b hashes for media files.

Files are only (re-)hashed when their stored hash is missing OR their
OS-level modification time has changed since the last hash was computed.
This prevents stale hashes from surviving silent file replacements.

Previously imported ``partial_md5`` / ``full_md5`` from hashing.py.  Those
functions were replaced with BLAKE2b equivalents (faster, no collisions);
this worker now imports the updated names.
"""
import logging
import os
from datetime import datetime, timezone

from PySide6.QtCore import Signal

from mlm.db.repositories.files_repo import FilesRepository
from mlm.utils.hashing import partial_blake2b, full_blake2b
from mlm.workers.base_worker import BaseWorker

log = logging.getLogger(__name__)

# Safe whitelist mapping mode -> column name, preventing SQL injection.
_MODE_TO_COLUMN: dict[str, str] = {
    "partial": "partial_hash",
    "full":    "full_hash",
}


class HashWorker(BaseWorker):
    """Hash media files in the background."""

    progress      = Signal(int, int, str)
    finished_hash = Signal(dict)

    def __init__(self, mode: str = "partial", limit: int = 0) -> None:
        super().__init__()
        if mode not in _MODE_TO_COLUMN:
            raise ValueError(f"mode must be one of {list(_MODE_TO_COLUMN)}, got {mode!r}")
        self.mode  = mode
        self.limit = limit
        self.repo  = FilesRepository()

    def _execute(self) -> None:
        column = _MODE_TO_COLUMN[self.mode]
        rows   = self.repo.list_files_needing_hash(column, self.limit)
        total  = len(rows)
        done   = errors = skipped = 0

        for index, row in enumerate(rows, start=1):
            if not self._running:
                break

            file_path = row["file_path"]
            file_id   = row["id"]

            try:
                stat   = os.stat(file_path)
                mtime  = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                digest = (
                    partial_blake2b(file_path)
                    if self.mode == "partial"
                    else full_blake2b(file_path)
                )
                self.repo.update_hash(file_id, column, digest, mtime)
                done += 1
            except FileNotFoundError:
                log.warning("Hash skipped — file not found: %s", file_path)
                skipped += 1
            except OSError as exc:
                log.warning("Hash OS error for %s: %s", file_path, exc)
                errors += 1
            except Exception as exc:
                log.error("Hash unexpected error for %s: %s", file_path, exc, exc_info=True)
                errors += 1

            self.progress.emit(index, total, file_path)

        self.finished_hash.emit({"done": done, "errors": errors, "skipped": skipped})
