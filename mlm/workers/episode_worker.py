from PySide6.QtCore import QThread, Signal
from mlm.services.episode_service import EpisodeService


class EpisodeWorker(QThread):
    finished_check = Signal(list)
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.service = EpisodeService()

    def run(self) -> None:
        try:
            result = self.service.check_all_shows()
            self.finished_check.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))