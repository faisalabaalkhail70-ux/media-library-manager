from PySide6.QtCore import QThread, Signal
from mlm.services.probe_service import ProbeService

class ProbeWorker(QThread):
    progress = Signal(int, int, str)
    finished_batch = Signal()
    failed = Signal(str)

    def __init__(self, limit: int = 300) -> None:
        super().__init__()
        self.limit = limit
        self._running = True
        self.service = ProbeService()

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        try:
            rows = self.service.list_files_needing_probe(self.limit)
            total = len(rows)

            for index, row in enumerate(rows, start=1):
                if not self._running:
                    break
                self.service.probe_file(row["id"], row["file_path"])
                self.progress.emit(index, total, row["file_path"])

            self.finished_batch.emit()
        except Exception as exc:
            self.failed.emit(str(exc))