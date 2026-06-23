"""QThread worker that walks a directory tree and records media files in the DB."""
import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from mlm.db.repositories.directories_repo import DirectoriesRepository
from mlm.db.repositories.files_repo import FilesRepository
from mlm.services.scan_service import ScanService

log = logging.getLogger(__name__)

DEFAULT_EXCLUDED_FOLDERS: frozenset[str] = frozenset({
    "extras", "sample", "samples", "behind the scenes",
    "featurettes", "interviews", "scenes", "shorts",
    "trailers", "deleted scenes", "specials", ".actors",
})


class ScanWorker(QThread):
    """Walk *root_path* recursively and upsert media file records."""

    progress      = Signal(int, str)
    finished_scan = Signal(dict)
    failed        = Signal(str)

    def __init__(
        self,
        directory_id: int,
        root_path: str,
        valid_exts: tuple[str, ...],
        excluded_folders: frozenset[str] | None = None,
        excluded_paths: set[str] | None = None,
    ) -> None:
        super().__init__()
        self.directory_id     = directory_id
        self.root_path        = Path(root_path).resolve()
        self.valid_exts       = {e.lower() for e in valid_exts}
        self.excluded_folders = excluded_folders or DEFAULT_EXCLUDED_FOLDERS
        self.excluded_paths   = {Path(p).resolve() for p in (excluded_paths or set())}
        self._running         = True
        self.scan_service     = ScanService()
        self.files_repo       = FilesRepository()
        self.directories_repo = DirectoriesRepository()

    def stop(self) -> None:
        self._running = False

    def _is_excluded(self, path: Path) -> bool:
        """Return True if path is inside an excluded folder name OR an excluded full path."""
        for excl in self.excluded_paths:
            try:
                path.relative_to(excl)
                return True
            except ValueError:
                pass

        try:
            rel_parts = path.relative_to(self.root_path).parts[:-1]
        except ValueError:
            return False
        return any(part.lower() in self.excluded_folders for part in rel_parts)

    def run(self) -> None:
        files_seen = files_added = files_updated = files_removed = 0
        scan_run_id = self.scan_service.begin_scan_run(self.directory_id)
        log.info("Scan started for directory_id=%d path=%s", self.directory_id, self.root_path)

        try:
            known_paths = self.files_repo.get_known_paths_for_directory(self.directory_id)
            seen_paths: set[str] = set()

            for path in self.root_path.rglob("*"):
                if not self._running:
                    self._finish(scan_run_id, files_seen, files_added, files_updated,
                                 files_removed, status="cancelled")
                    return

                if not path.is_file():
                    continue
                if path.suffix.lower() not in self.valid_exts:
                    continue
                if self._is_excluded(path):
                    continue

                path_str = str(path)
                seen_paths.add(path_str)
                was_known = path_str in known_paths

                try:
                    self.scan_service.save_file_record(self.directory_id, path)
                except OSError as exc:
                    # File disappeared between rglob discovery and stat() — skip gracefully.
                    log.warning("Skipped %s (file vanished during scan): %s", path, exc)
                    seen_paths.discard(path_str)  # don't count it as seen
                    continue
                except Exception as exc:
                    # Unexpected error: log it but keep the scan running.
                    log.error("Unexpected error saving %s: %s", path, exc, exc_info=True)
                    continue

                files_seen += 1
                if was_known:
                    files_updated += 1
                else:
                    files_added += 1

                if files_seen % 10 == 0:
                    self.progress.emit(files_seen, path.name)

            now = datetime.now().isoformat(timespec="seconds")
            for missing_path in known_paths - seen_paths:
                self.files_repo.mark_removed(missing_path, now)
                files_removed += 1
                log.debug("Marked removed: %s", missing_path)

            self.directories_repo.update_last_scanned(self.directory_id, now)
            self._finish(scan_run_id, files_seen, files_added, files_updated, files_removed)

        except Exception as exc:
            log.exception("ScanWorker failed for directory_id=%d", self.directory_id)
            self.scan_service.finish_scan_run(
                scan_run_id,
                files_seen=files_seen, files_added=files_added,
                files_updated=files_updated, files_removed=files_removed,
                status="failed", error_message=str(exc),
            )
            self.failed.emit(str(exc))

    def _finish(
        self,
        scan_run_id: int,
        files_seen: int,
        files_added: int,
        files_updated: int,
        files_removed: int,
        status: str = "completed",
    ) -> None:
        self.scan_service.finish_scan_run(
            scan_run_id,
            files_seen=files_seen, files_added=files_added,
            files_updated=files_updated, files_removed=files_removed,
            status=status,
        )
        log.info("Scan %s \u2014 seen=%d added=%d updated=%d removed=%d",
                 status, files_seen, files_added, files_updated, files_removed)
        self.finished_scan.emit({
            "status":        status,
            "files_seen":    files_seen,
            "files_added":   files_added,
            "files_removed": files_removed,
        })
