"""R-6 SnapshotWorker — takes / diffs library snapshots off the UI thread.

Signals
-------
  finished_snapshot(int)           — emits the new snapshot_id
  finished_diff(str)               — emits the plain-text diff report
"""
from __future__ import annotations

import logging

from PySide6.QtCore import Signal

from mlm.services.snapshot_service import SnapshotService
from mlm.workers.base_worker import BaseWorker

log = logging.getLogger(__name__)


class SnapshotWorker(BaseWorker):
    """Background worker for snapshot take / diff operations."""

    finished_snapshot = Signal(int)
    finished_diff     = Signal(str)

    def __init__(
        self,
        operation: str,                # 'take' | 'diff'
        label: str = "",
        snap_a_id: int | None = None,
        snap_b_id: int | None = None,
    ) -> None:
        super().__init__()
        self._op       = operation
        self._label    = label
        self._snap_a   = snap_a_id
        self._snap_b   = snap_b_id
        self._svc      = SnapshotService()

    def _execute(self) -> None:
        if self._op == "take":
            snap_id = self._svc.take_snapshot(label=self._label)
            self.finished_snapshot.emit(snap_id)
        elif self._op == "diff":
            if self._snap_a is None:
                raise ValueError("snap_a_id is required for diff operation")
            diff   = self._svc.diff(self._snap_a, self._snap_b, latest=(self._snap_b is None))
            report = self._svc.format_diff_report(diff)
            self.finished_diff.emit(report)
        else:
            raise ValueError(f"Unknown SnapshotWorker operation: '{self._op}'")
