from PySide6.QtCore import QThread, Signal

from mlm.services.undo_service import UndoService


class UndoWorker(QThread):
    finished_undo = Signal(dict)
    failed = Signal(str)

    def __init__(self, limit: int = 20) -> None:
        super().__init__()
        self.limit = limit
        self.service = UndoService()

    def run(self) -> None:
        try:
            result = self.service.undo_latest_renames(limit=self.limit)
            self.finished_undo.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))