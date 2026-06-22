import logging
from PySide6.QtCore import QThread, Signal
from mlm.services.probe_service import ProbeService

log = logging.getLogger(__name__)


class ProbeWorker(QThread):
    progress       = Signal(int, int, str)   # current, total, path
    file_error     = Signal(str, str)        # file_path, error_message
    finished_batch = Signal()
    failed         = Signal(str)

    def __init__(self, limit: int = 0) -> None:
        """limit=0 (default) processes ALL files needing probe."""
        super().__init__()
        self.limit    = limit
        self._running = True
        self.service  = ProbeService()

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        try:
            rows  = self.service.list_files_needing_probe(self.limit)
            total = len(rows)

            for index, row in enumerate(rows, start=1):
                if not self._running:
                    break
                try:
                    self.service.probe_file(row["id"], row["file_path"])
                except Exception as exc:
                    error_msg = str(exc)
                    log.warning("ffprobe failed for %s: %s", row["file_path"], error_msg)
                    # Mark the file as errored in the DB so it is skipped on next run
                    try:
                        self.service.mark_probe_error(row["id"], error_msg)
                    except Exception:
                        pass
                    # Notify the UI — it will decide whether to ask the user
                    self.file_error.emit(row["file_path"], error_msg)

                self.progress.emit(index, total, row["file_path"])

            self.finished_batch.emit()
        except Exception as exc:
            self.failed.emit(str(exc))
