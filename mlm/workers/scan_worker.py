from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from mlm.services.scan_service import ScanService
from mlm.db.repositories.files_repo import FilesRepository
from mlm.db.repositories.directories_repo import DirectoriesRepository

DEFAULT_EXCLUDED_FOLDERS = {
    "extras", "sample", "samples", "behind the scenes",
    "featurettes", "interviews", "scenes", "shorts",
    "trailers", "deleted scenes", "specials", ".actors",
}


class ScanWorker(QThread):
    progress = Signal(int, str)
    finished_scan = Signal(dict)
    failed = Signal(str)

    def __init__(
        self,
        directory_id: int,
        root_path: str,
        valid_exts: tuple[str, ...],
        excluded_folders: set[str] | None = None,
    ) -> None:
        super().__init__()
        self.directory_id = directory_id
        self.root_path = Path(root_path).resolve()
        self.valid_exts = set(valid_exts)
        self.excluded_folders = excluded_folders or DEFAULT_EXCLUDED_FOLDERS
        self._running = True
        self.scan_service = ScanService()
        self.files_repo = FilesRepository()
        self.directories_repo = DirectoriesRepository()

    def stop(self) -> None:
        self._running = False

    def _is_excluded(self, path: Path) -> bool:
        for part in path.relative_to(self.root_path).parts[:-1]:
            if part.lower() in self.excluded_folders:
                return True
        return False

    def run(self) -> None:
        files_seen = 0
        files_added = 0
        files_updated = 0
        files_removed = 0
        scan_run_id = self.scan_service.begin_scan_run(self.directory_id)

        try:
            # ── كل المسارات المعروفة في DB لهذا المجلد ──────────
            known_paths = self.files_repo.get_known_paths_for_directory(
                self.directory_id
            )
            seen_paths: set[str] = set()

            for path in self.root_path.rglob("*"):
                if not self._running:
                    self.scan_service.finish_scan_run(
                        scan_run_id,
                        files_seen=files_seen,
                        files_added=files_added,
                        files_updated=files_updated,
                        files_removed=files_removed,
                        status="cancelled",
                    )
                    self.finished_scan.emit({
                        "status": "cancelled",
                        "files_seen": files_seen,
                        "files_added": files_added,
                        "files_removed": files_removed,
                    })
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
                self.scan_service.save_file_record(self.directory_id, path)
                files_seen += 1

                if was_known:
                    files_updated += 1
                else:
                    files_added += 1

                if files_seen % 10 == 0:
                    self.progress.emit(files_seen, path.name)

            # ── الملفات التي اختفت من القرص ──────────────────────
            now = datetime.now().isoformat(timespec="seconds")
            for missing_path in known_paths - seen_paths:
                self.files_repo.mark_removed(missing_path, now)
                files_removed += 1

            # ── تحديث last_scanned_at ─────────────────────────────
            self.directories_repo.update_last_scanned(self.directory_id, now)

            self.scan_service.finish_scan_run(
                scan_run_id,
                files_seen=files_seen,
                files_added=files_added,
                files_updated=files_updated,
                files_removed=files_removed,
                status="completed",
            )
            self.finished_scan.emit({
                "status": "completed",
                "files_seen": files_seen,
                "files_added": files_added,
                "files_removed": files_removed,
            })

        except Exception as exc:
            self.scan_service.finish_scan_run(
                scan_run_id,
                files_seen=files_seen,
                files_added=files_added,
                files_updated=files_updated,
                files_removed=files_removed,
                status="failed",
                error_message=str(exc),
            )
            self.failed.emit(str(exc))