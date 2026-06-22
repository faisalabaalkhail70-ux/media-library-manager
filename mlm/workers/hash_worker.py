"""QThread worker that computes partial or full MD5 hashes for media files.

Files are only (re-)hashed when their stored hash is missing OR their
OS-level modification time has changed since the last hash was computed.
This prevents stale hashes from surviving silent file replacements.
"""
import logging
import os
from datetime import datetime, timezone

from PySide6.QtCore import QThread, Signal

from mlm.db.repositories.files_repo import FilesRepository
from mlm.utils.hashing import partial_md5, full_md5

log = logging.getLogger(__name__)

# Safe whitelist mapping mode -> column name, preventing SQL injection.
_MODE_TO_COLUMN: dict[str, str] = {
    "partial": "partial_hash",
    "full": "full_hash",
}


def _current_mtime_iso(path: str) -> str | None:
    """Return the file's mtime as a UTC ISO-8601 string, or None if unreadable."""
    try:
        ts = os.path.getmtime(path)
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")
    except OSError:
        return None


class HashWorker(QThread):
    """Compute partial or full file hashes in a background thread.

    A file is skipped if it already has a hash AND its stored
    ``modified_at`` matches the current OS mtime — meaning it has not
    changed since it was last hashed.

    Args:
        mode: ``"partial"`` (fast, first 10 MB) or ``"full"`` (entire file).
    """

    progress = Signal(int, int)   # (done, total)
    finished = Signal(int)        # files_hashed
    failed = Signal(str)

    def __init__(self, mode: str = "partial") -> None:
        super().__init__()
        if mode not in _MODE_TO_COLUMN:
            raise ValueError(
                f"Invalid hash mode '{mode}'. Must be one of {list(_MODE_TO_COLUMN)}."
            )
        self.mode = mode
        self.repo = FilesRepository()
        self._running = True

    def stop(self) -> None:
        """Signal the worker to stop after the current file."""
        self._running = False

    def run(self) -> None:
        """Hash all stale/unhashed files and emit progress signals."""
        try:
            files = self._get_files_needing_hash()
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

                    # Persist the current mtime so future runs can skip unchanged files
                    mtime = _current_mtime_iso(path)
                    if mtime:
                        self.repo.update_modified_at(path, mtime)

                except OSError as exc:
                    log.warning("Skipping unreadable file %s: %s", path, exc)
                except Exception as exc:
                    log.error(
                        "Unexpected error hashing %s: %s", path, exc, exc_info=True
                    )

                done += 1
                if done % 5 == 0:
                    self.progress.emit(done, total)

            self.finished.emit(done)

        except Exception as exc:
            log.exception("HashWorker crashed")
            self.failed.emit(str(exc))

    def _get_files_needing_hash(self) -> list[dict]:
        """Return files that need (re-)hashing.

        A file needs hashing when:
        * its hash column is NULL, OR
        * its stored ``modified_at`` differs from the current OS mtime
          (the file has been replaced or modified since the last hash).
        """
        from mlm.db.connection import get_connection

        col = _MODE_TO_COLUMN[self.mode]  # safe: validated in __init__
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT id, file_path, file_size_bytes, modified_at
                FROM media_files
                WHERE removed_at IS NULL
                  AND {col} IS NULL
                ORDER BY file_size_bytes DESC
                """
            ).fetchall()

        candidates = [dict(r) for r in rows]

        # Also check files that HAVE a hash but whose mtime has changed
        with get_connection() as conn:
            hashed_rows = conn.execute(
                f"""
                SELECT id, file_path, file_size_bytes, modified_at
                FROM media_files
                WHERE removed_at IS NULL
                  AND {col} IS NOT NULL
                  AND modified_at IS NOT NULL
                """
            ).fetchall()

        for row in hashed_rows:
            current_mtime = _current_mtime_iso(row["file_path"])
            if current_mtime and current_mtime != row["modified_at"]:
                log.debug(
                    "mtime changed for %s (stored=%s current=%s) — will re-hash",
                    row["file_path"], row["modified_at"], current_mtime,
                )
                candidates.append(dict(row))

        return candidates
