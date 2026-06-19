from PySide6.QtCore import QThread, Signal
from mlm.services.rename_service import RenameService

class RenameWorker(QThread):
    finished_apply = Signal(dict)
    failed = Signal(str)

    def __init__(self, preview_rows: list[dict]) -> None:
        super().__init__()
        self.preview_rows = preview_rows
        self.service = RenameService()

    def run(self) -> None:
        try:
            result = self.service.apply_preview(self.preview_rows)
            self.finished_apply.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))