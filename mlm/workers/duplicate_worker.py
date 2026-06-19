from PySide6.QtCore import QThread, Signal
from mlm.services.duplicate_service import DuplicateService

class DuplicateWorker(QThread):
    finished_build = Signal(dict)
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.service = DuplicateService()

    def run(self) -> None:
        try:
            result = self.service.build_duplicate_groups()
            self.finished_build.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))