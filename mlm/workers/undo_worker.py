"""Background worker that undoes the most recent batch of renames."""
import logging

from PySide6.QtCore import Signal

from mlm.services.undo_service import UndoService
from mlm.workers.base_worker import BaseWorker

log = logging.getLogger(__name__)


class UndoWorker(BaseWorker):
    """Undo the latest rename actions in the background."""

    finished_undo = Signal(dict)

    def __init__(self, limit: int = 20) -> None:
        super().__init__()
        self.limit = limit
        self.service = UndoService()

    def _execute(self) -> None:
        result = self.service.undo_latest_renames(limit=self.limit)
        self.finished_undo.emit(result)
