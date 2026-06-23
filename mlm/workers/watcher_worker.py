"""H-1 WatcherWorker — thin QThread that manages the WatcherService lifecycle.

This worker starts the watchdog observer threads when the app launches
and exposes the same file_added / file_removed / file_moved / sub_added
signals as WatcherService so the main window can connect directly.

Usage (in MainWindow.__init__)
------------------------------
    self.watcher_worker = WatcherWorker()
    self.watcher_worker.file_added.connect(self.on_file_added)
    self.watcher_worker.start()
    ...
    # on shutdown:
    self.watcher_worker.stop()
    self.watcher_worker.wait(3000)
"""
from __future__ import annotations

import logging

from PySide6.QtCore import Signal

from mlm.services.watcher_service import WatcherService
from mlm.workers.base_worker import BaseWorker

log = logging.getLogger(__name__)


class WatcherWorker(BaseWorker):
    """Starts WatcherService in a background thread."""

    file_added   = Signal(str)
    file_removed = Signal(str)
    file_moved   = Signal(str, str)
    sub_added    = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._svc: WatcherService | None = None

    def _execute(self) -> None:
        self._svc = WatcherService()
        # Forward signals from service to worker (thread-safe via Qt queued connections)
        self._svc.file_added.connect(self.file_added)
        self._svc.file_removed.connect(self.file_removed)
        self._svc.file_moved.connect(self.file_moved)
        self._svc.sub_added.connect(self.sub_added)

        # Auto-upsert new files into the DB
        self._svc.file_added.connect(self._svc.handle_new_file)

        self._svc.start_all()
        log.info("[WatcherWorker] Filesystem watching active.")

        # Block until stop() is called
        while self._running:
            self.msleep(500)

        self._svc.stop_all()
        log.info("[WatcherWorker] Filesystem watching stopped.")
