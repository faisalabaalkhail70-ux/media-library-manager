from PySide6.QtCore import QThread, Signal
from mlm.services.health_service import HealthService


class HealthWorker(QThread):
    finished_scan = Signal(dict)
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.service = HealthService()

    def run(self) -> None:
        try:
            result = self.service.run_health_scan()
            self.finished_scan.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))