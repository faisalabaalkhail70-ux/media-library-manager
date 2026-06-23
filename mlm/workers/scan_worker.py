"""Directory scan worker.

Changes in v1.1
---------------
* Inherits from BaseWorker — no more copy-paste stop/failed boilerplate.
* TOCTOU fix: OSError on individual files is caught and skipped gracefully
  instead of aborting the entire scan run (issue #5).
* Unexpected errors per-file are logged but scanning continues.
* Counter increments use explicit if/else instead of bool arithmetic.
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Signal

from mlm.services.scan_service import ScanService
from mlm.workers.base_worker import BaseWorker

log = logging.getLogger(__name__)


class ScanWorker(BaseWorker):
    """Scans a watched directory and upserts file records into the DB."""

    progress = Signal(int, int, str)   # files_done, total, current_path
    finished = Signal(dict)            # summary dict

    def __init__(self, directory_id: int, directory_path: str) -> None:
        super().__init__()
        self.directory_id   = directory_id
        self.directory_path = directory_path
        self.scan_service   = ScanService()

    def _execute(self) -> None:
        log.info(
            "Scan started: %s (dir_id=%d)", self.directory_path, self.directory_id
        )

        try:
            all_paths = [
                p
                for p in Path(self.directory_path).rglob("*")
                if p.is_file() and not p.name.startswith(".")
            ]
        except OSError as exc:
            raise RuntimeError(
                f"Cannot read directory '{self.directory_path}': {exc}"
            ) from exc

        total         = len(all_paths)
        files_added   = 0
        files_updated = 0
        files_skipped = 0

        for i, path in enumerate(all_paths, start=1):
            if not self._running:
                log.info("Scan cancelled after %d/%d files.", i - 1, total)
                break

            self.progress.emit(i, total, str(path))

            try:
                was_known = self.scan_service.save_file_record(
                    self.directory_id, path
                )
            except OSError as exc:
                # File disappeared between discovery and stat — skip gracefully
                log.warning("Skipped '%s' (OSError — file may have moved): %s", path, exc)
                files_skipped += 1
                continue
            except Exception as exc:  # noqa: BLE001
                log.error(
                    "Unexpected error saving '%s': %s", path, exc, exc_info=True
                )
                files_skipped += 1
                continue

            if was_known:
                files_updated += 1
            else:
                files_added += 1

        summary = {
            "total":         total,
            "files_added":   files_added,
            "files_updated": files_updated,
            "files_skipped": files_skipped,
        }
        log.info("Scan finished: %s", summary)
        self.finished.emit(summary)
