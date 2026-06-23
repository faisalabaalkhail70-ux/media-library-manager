"""Background worker that runs a full health scan."""
from PySide6.QtCore import Signal

from mlm.workers.base_worker import BaseWorker
from mlm.services.health_service import HealthService


class HealthWorker(BaseWorker):
    """Run a full health scan in a background thread."""

    finished_scan = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.service = HealthService()

    def _execute(self) -> None:
        result = self.service.run_health_scan()
        self.finished_scan.emit(result)
