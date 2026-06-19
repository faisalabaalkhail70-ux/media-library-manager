from PySide6.QtCore import QThread, Signal
from mlm.db.repositories.episodes_repo import EpisodesRepository
from mlm.services.episode_service import EpisodeService

class EpisodeWorker(QThread):
    progress = Signal(int, int, str)
    finished_batch = Signal(list)
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.repo = EpisodesRepository()
        self.service = EpisodeService()
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        try:
            shows = self.repo.list_show_entities()
            total = len(shows)
            results = []

            for index, show in enumerate(shows, start=1):
                if not self._running:
                    break
                result = self.service.check_show_missing(show["id"], show["tmdb_id"])
                results.append(result)
                self.progress.emit(index, total, result["show_title"])

            self.finished_batch.emit(results)
        except Exception as exc:
            self.failed.emit(str(exc))