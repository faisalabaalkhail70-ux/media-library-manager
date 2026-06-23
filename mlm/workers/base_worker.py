"""BaseWorker — shared QThread plumbing for all background workers.

Every worker subclasses this instead of QThread directly::

    class MyScanWorker(BaseWorker):
        finished = Signal(dict)

        def _execute(self) -> None:
            result = do_work()
            self.finished.emit(result)

The base class provides:
  - ``failed = Signal(str)`` emitted on unhandled exceptions in _execute
  - ``_running`` flag set to False by ``stop()``
  - ``run()`` wrapper that calls ``_execute()`` inside a try/except
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QThread, Signal

log = logging.getLogger(__name__)


class BaseWorker(QThread):
    """Common plumbing shared by all background workers."""

    failed: Signal = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._running: bool = True

    def stop(self) -> None:
        """Signal the worker to stop gracefully on the next iteration."""
        self._running = False

    def run(self) -> None:
        try:
            self._execute()
        except Exception as exc:  # noqa: BLE001
            log.exception("Worker %s raised: %s", self.__class__.__name__, exc)
            self.failed.emit(str(exc))

    def _execute(self) -> None:
        """Override in subclasses. Called inside a try/except by run()."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement _execute()")
