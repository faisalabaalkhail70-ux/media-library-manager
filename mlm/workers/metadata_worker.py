"""Background worker that auto-matches unmatched files against TMDB."""
from PySide6.QtCore import Signal

from mlm.workers.base_worker import BaseWorker
from mlm.services.metadata_service import MetadataService


class MetadataWorker(BaseWorker):
    """Auto-match unmatched media files against TMDB in a background thread."""

    progress       = Signal(int, int, str)
    finished_batch = Signal()

    def __init__(self, limit: int = 0, force: bool = False) -> None:
        """limit=0 (default) processes ALL unmatched files."""
        super().__init__()
        self.limit = limit
        self.force = force
        self.service = MetadataService()

    def _execute(self) -> None:
        rows = self.service.list_unmatched_files(self.limit)
        total = len(rows)
        if total == 0:
            self.finished_batch.emit()
            return

        for index, row in enumerate(rows, start=1):
            if not self._running:
                break
            result = self.service.auto_match_file(row["id"], row["file_name"])
            label = result.get("title") or row["file_name"]
            self.progress.emit(index, total, label)

        self.finished_batch.emit()
