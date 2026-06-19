from pathlib import Path
from PySide6.QtCore import QThread, Signal
from mlm.services.scan_service import ScanService

class ScanWorker(QThread):
    progress = Signal(int, str)
    finished_scan = Signal(dict)
    failed = Signal(str)

    def __init__(self, directory_id: int, root_path: str, valid_exts: tuple[str, ...]) -> None:
        super().__init__()
        self.directory_id = directory_id
        self.root_path = Path(root_path)
        self.valid_exts = set(valid_exts)
        self._running = True
        self.scan_service = ScanService()

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        files_seen = 0
        files_added = 0
        scan_run_id = self.scan_service.begin_scan_run(self.directory_id)

        try:
            for path in self.root_path.rglob("*"):
                if not self._running:
                    self.scan_service.finish_scan_run(
                        scan_run_id,
                        files_seen=files_seen,
                        files_added=files_added,
                        status="cancelled",
                    )
                    self.finished_scan.emit({
                        "status": "cancelled",
                        "files_seen": files_seen,
                        "files_added": files_added,
                    })
                    return

                if not path.is_file():
                    continue

                if path.suffix.lower() not in self.valid_exts:
                    continue

                self.scan_service.save_file_record(self.directory_id, path)
                files_seen += 1
                files_added += 1

                if files_seen % 10 == 0:
                    self.progress.emit(files_seen, path.name)

            self.scan_service.finish_scan_run(
                scan_run_id,
                files_seen=files_seen,
                files_added=files_added,
                status="completed",
            )
            self.finished_scan.emit({
                "status": "completed",
                "files_seen": files_seen,
                "files_added": files_added,
            })

        except Exception as exc:
            self.scan_service.finish_scan_run(
                scan_run_id,
                files_seen=files_seen,
                files_added=files_added,
                status="failed",
                error_message=str(exc),
            )
            self.failed.emit(str(exc))