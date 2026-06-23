"""Background worker that scans for duplicate media files."""
from PySide6.QtCore import Signal

from mlm.workers.base_worker import BaseWorker
from mlm.services.duplicate_service import DuplicateService


class DuplicateWorker(BaseWorker):
    """Scan for duplicate media files in a background thread."""

    finished_build = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.service = DuplicateService()

    def _execute(self) -> None:
        result = self.service.build_duplicate_groups()
        self.finished_build.emit(result)
