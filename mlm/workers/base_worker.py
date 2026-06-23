"""Shared base class for all background QThread workers.

All workers in this package share identical boilerplate:
  - ``failed = Signal(str)``
  - ``_running`` cancellation flag
  - ``stop()`` method
  - ``run()`` with a top-level try/except that emits ``failed``

Subclasses override ``_execute()`` instead of ``run()``.
"""
import logging

from PySide6.QtCore import QThread, Signal

log = logging.getLogger(__name__)


class BaseWorker(QThread):
    """Common plumbing shared by all background workers.

    Subclass and override ``_execute()``:

    .. code-block:: python

        class MyWorker(BaseWorker):
            finished = Signal(dict)

            def __init__(self) -> None:
                super().__init__()
                self.service = MyService()

            def _execute(self) -> None:
                result = self.service.do_work(self._running_fn)
                self.finished.emit(result)
    """

    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._running = True

    def stop(self) -> None:
        """Request graceful cancellation.  Workers check ``_running`` in their loop."""
        self._running = False

    def _running_fn(self) -> bool:
        """Callable form of the running flag, suitable for passing to services."""
        return self._running

    def run(self) -> None:
        """Entry point called by Qt.  Do not override — override ``_execute()`` instead."""
        try:
            self._execute()
        except Exception as exc:
            log.exception("%s failed: %s", type(self).__name__, exc)
            self.failed.emit(str(exc))

    def _execute(self) -> None:
        """Override in subclasses to implement the worker\'s actual logic."""
        raise NotImplementedError(f"{type(self).__name__} must implement _execute()")
