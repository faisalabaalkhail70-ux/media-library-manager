"""Background worker that applies a rename preview to disk and the DB."""
import logging

from PySide6.QtCore import Signal

from mlm.services.rename_service import RenameService
from mlm.workers.base_worker import BaseWorker

log = logging.getLogger(__name__)


class RenameWorker(BaseWorker):
    """Apply a rename preview list in the background."""

    finished_apply = Signal(dict)

    def __init__(self, preview_rows: list[dict]) -> None:
        super().__init__()
        self.preview_rows = preview_rows
        self.service = RenameService()

    def _execute(self) -> None:
        result = self.service.apply_preview(self.preview_rows)
        self.finished_apply.emit(result)
