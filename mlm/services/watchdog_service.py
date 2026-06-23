"""H-1 — Real-time filesystem watcher using the `watchdog` library.

Dispatch rules
--------------
*Created / Modified*  →  ScanService.save_file_record() (upsert)
*Deleted*             →  mark is_missing = 1 in media_files
*Moved / Renamed*     →  UPDATE media_files SET file_path = new_path

Events are debounced (500 ms) to avoid bursts from copy operations.
A thread-safe Qt signal bridge allows views to subscribe to updates
without subclassing QThread.

Usage
-----
    bridge = WatchdogBridge()          # QObject, lives on main thread
    bridge.file_added.connect(view.on_file_added)

    svc = WatchdogService(bridge)
    svc.watch(directory_id=1, path="/mnt/media/movies")
    # ... later ...
    svc.unwatch(directory_id=1)
    svc.stop_all()
"""
from __future__ import annotations

import logging
import time
import threading
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Signal

from mlm.app.config import AppConfig
from mlm.db.connection import get_connection

log = logging.getLogger(__name__)

_cfg = AppConfig()
_DEBOUNCE_S = 0.5   # seconds


# ---------------------------------------------------------------------------
# Qt signal bridge (lives on the GUI thread)
# ---------------------------------------------------------------------------

class WatchdogBridge(QObject):
    """Emits Qt signals whenever the watchdog sees filesystem changes."""
    file_added    = Signal(str)   # file_path
    file_modified = Signal(str)
    file_deleted  = Signal(str)
    file_moved    = Signal(str, str)   # old_path, new_path


# ---------------------------------------------------------------------------
# Debounce helper
# ---------------------------------------------------------------------------

class _Debouncer:
    """Call *fn* at most once per *delay* seconds for a given key."""

    def __init__(self, delay: float) -> None:
        self._delay = delay
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def call(self, key: str, fn: Callable[[], None]) -> None:
        with self._lock:
            if key in self._timers:
                self._timers[key].cancel()
            t = threading.Timer(self._delay, fn)
            self._timers[key] = t
            t.start()

    def cancel_all(self) -> None:
        with self._lock:
            for t in self._timers.values():
                t.cancel()
            self._timers.clear()


# ---------------------------------------------------------------------------
# Watchdog event handler
# ---------------------------------------------------------------------------

class _MLMEventHandler:
    """Watchdog-compatible event handler (plain class, no watchdog base needed)."""

    def __init__(
        self,
        directory_id: int,
        bridge: WatchdogBridge,
        debouncer: _Debouncer,
    ) -> None:
        self._dir_id = directory_id
        self._bridge = bridge
        self._deb = debouncer

    def _is_media(self, path: str) -> bool:
        return Path(path).suffix.lower() in _cfg.supported_video_exts

    def dispatch(self, event) -> None:  # type: ignore[no-untyped-def]
        """Called by watchdog for every filesystem event."""
        et = type(event).__name__
        if et in ("FileCreatedEvent", "FileModifiedEvent"):
            if self._is_media(event.src_path):
                self._deb.call(
                    event.src_path,
                    lambda p=event.src_path: self._on_upsert(p),
                )
        elif et == "FileDeletedEvent":
            if self._is_media(event.src_path):
                self._deb.call(
                    event.src_path,
                    lambda p=event.src_path: self._on_deleted(p),
                )
        elif et == "FileMovedEvent":
            if self._is_media(event.src_path) or self._is_media(event.dest_path):
                self._deb.call(
                    event.src_path,
                    lambda s=event.src_path, d=event.dest_path: self._on_moved(s, d),
                )

    # ---- actions ----------------------------------------------------------

    def _on_upsert(self, path: str) -> None:
        try:
            from mlm.services.scan_service import ScanService
            ScanService().save_file_record(self._dir_id, Path(path))
            log.info("Watchdog upserted: %s", path)
            self._bridge.file_added.emit(path)
        except Exception as exc:  # noqa: BLE001
            log.error("Watchdog upsert failed for %s: %s", path, exc)

    def _on_deleted(self, path: str) -> None:
        try:
            with get_connection() as conn:
                conn.execute(
                    "UPDATE media_files SET is_missing=1 WHERE file_path=?",
                    (path,),
                )
            log.info("Watchdog marked missing: %s", path)
            self._bridge.file_deleted.emit(path)
        except Exception as exc:  # noqa: BLE001
            log.error("Watchdog delete-mark failed for %s: %s", path, exc)

    def _on_moved(self, old_path: str, new_path: str) -> None:
        try:
            with get_connection() as conn:
                conn.execute(
                    "UPDATE media_files SET file_path=?, file_name=? WHERE file_path=?",
                    (new_path, Path(new_path).name, old_path),
                )
            log.info("Watchdog renamed: %s → %s", old_path, new_path)
            self._bridge.file_moved.emit(old_path, new_path)
        except Exception as exc:  # noqa: BLE001
            log.error("Watchdog rename failed %s: %s", old_path, exc)


# ---------------------------------------------------------------------------
# WatchdogService
# ---------------------------------------------------------------------------

class WatchdogService:
    """Manages watchdog observers for multiple directories."""

    def __init__(self, bridge: WatchdogBridge) -> None:
        self._bridge = bridge
        self._debouncer = _Debouncer(_DEBOUNCE_S)
        self._observers: dict[int, object] = {}   # dir_id → Observer

    def watch(self, directory_id: int, path: str) -> None:
        """Start watching *path* for *directory_id*.  Idempotent."""
        if directory_id in self._observers:
            return
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            handler = _MLMEventHandler(directory_id, self._bridge, self._debouncer)

            # Wrap in a watchdog-compatible class
            class _Adapter(FileSystemEventHandler):
                def dispatch(self_, event):  # type: ignore[override]
                    handler.dispatch(event)

            obs = Observer()
            obs.schedule(_Adapter(), path, recursive=True)
            obs.start()
            self._observers[directory_id] = obs
            log.info("Watchdog started for dir %d: %s", directory_id, path)
        except ImportError:
            log.warning(
                "watchdog package not installed — real-time monitoring unavailable. "
                "Install with: pip install watchdog"
            )
        except Exception as exc:  # noqa: BLE001
            log.error("Failed to start watchdog for %s: %s", path, exc)

    def unwatch(self, directory_id: int) -> None:
        obs = self._observers.pop(directory_id, None)
        if obs:
            try:
                obs.stop()    # type: ignore[attr-defined]
                obs.join(timeout=5)  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001
                log.warning("Error stopping observer: %s", exc)

    def stop_all(self) -> None:
        self._debouncer.cancel_all()
        for dir_id in list(self._observers):
            self.unwatch(dir_id)

    def watch_all_enabled_directories(self) -> None:
        """Convenience: load all enabled dirs from DB and watch them."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, path FROM directories WHERE is_enabled = 1"
            ).fetchall()
        for row in rows:
            self.watch(row["id"], row["path"])
