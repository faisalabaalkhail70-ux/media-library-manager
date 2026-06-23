"""Background worker that checks all shows for missing episodes."""
import logging

from PySide6.QtCore import Signal

from mlm.services.episode_service import EpisodeService
from mlm.workers.base_worker import BaseWorker

log = logging.getLogger(__name__)


class EpisodeWorker(BaseWorker):
    """Run the missing-episode check in the background."""

    finished_check = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.service = EpisodeService()

    def _execute(self) -> None:
        result = self.service.check_all_shows()
        self.finished_check.emit(result)
