"""E-4 RestructureWorker — runs FolderRestructureService in a QThread.

Emits progress(done, total, current_path) and finished(results_list).
The main window connects to these and updates a progress dialog.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import Signal

from mlm.services.folder_restructure_service import FolderRestructureService
from mlm.workers.base_worker import BaseWorker

log = logging.getLogger(__name__)


class RestructureWorker(BaseWorker):
    """Moves media files to their canonical locations in a background thread."""

    progress = Signal(int, int, str)   # done, total, current_path
    finished = Signal(list)            # list[dict] results

    def __init__(
        self,
        base_dir: str,
        directory_id: int | None = None,
        dry_run: bool = True,
        movie_template: str | None = None,
        show_template: str | None = None,
    ) -> None:
        super().__init__()
        kwargs: dict = {"base_dir": base_dir}
        if movie_template:
            kwargs["movie_template"] = movie_template
        if show_template:
            kwargs["show_template"] = show_template
        self._svc          = FolderRestructureService(**kwargs)
        self._directory_id = directory_id
        self._dry_run      = dry_run

    def _execute(self) -> None:
        from mlm.db.connection import get_connection
        with get_connection() as conn:
            if self._directory_id is not None:
                rows = conn.execute(
                    "SELECT id, file_path FROM media_files "
                    "WHERE removed_at IS NULL AND directory_id=?",
                    (self._directory_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, file_path FROM media_files WHERE removed_at IS NULL"
                ).fetchall()

        total   = len(rows)
        results = []

        for i, row in enumerate(rows, start=1):
            if not self._running:
                log.info("[RestructureWorker] Cancelled at %d/%d", i - 1, total)
                break
            self.progress.emit(i, total, row["file_path"])
            result = self._svc.move_file(row["id"], dry_run=self._dry_run)
            results.append(result)

        self.finished.emit(results)
        log.info(
            "[RestructureWorker] Done: %d files processed (%s).",
            len(results),
            "DRY RUN" if self._dry_run else "LIVE",
        )
