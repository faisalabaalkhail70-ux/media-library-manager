"""H-1 Filesystem Watcher — real-time directory monitoring via watchdog.

The WatcherService manages one watchdog Observer per watched directory.
When new media files appear or are removed, it emits Qt-compatible
signals through a QObject bridge so the UI can react without polling.

Integration
-----------
    from mlm.services.watcher_service import WatcherService

    watcher = WatcherService()
    watcher.file_added.connect(lambda path: print('New file:', path))
    watcher.file_removed.connect(lambda path: print('Gone:', path))
    watcher.start_all()          # watch all enabled directories
    ...
    watcher.stop_all()
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from mlm.app.config import AppConfig
from mlm.db.connection import get_connection

log = logging.getLogger(__name__)
_cfg = AppConfig()
_MEDIA_EXTS: frozenset[str] = frozenset(_cfg.supported_video_exts)
_SUB_EXTS:   frozenset[str] = frozenset({".srt", ".ass", ".ssa", ".vtt", ".sub"})


class _EventBridge(QObject):
    """Thread-safe Qt signal bridge for watchdog callbacks."""
    file_added   = Signal(str)
    file_removed = Signal(str)
    file_moved   = Signal(str, str)   # old_path, new_path
    sub_added    = Signal(str)        # subtitle path


class _MediaHandler(FileSystemEventHandler):
    """Watchdog event handler: filters events to media/subtitle files only."""

    def __init__(self, bridge: _EventBridge) -> None:
        super().__init__()
        self._bridge = bridge

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        p = Path(event.src_path)
        if p.suffix.lower() in _MEDIA_EXTS:
            log.debug("[Watcher] New media: %s", p)
            self._bridge.file_added.emit(str(p))
        elif p.suffix.lower() in _SUB_EXTS:
            log.debug("[Watcher] New subtitle: %s", p)
            self._bridge.sub_added.emit(str(p))

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        p = Path(event.src_path)
        if p.suffix.lower() in _MEDIA_EXTS:
            log.debug("[Watcher] Removed: %s", p)
            self._bridge.file_removed.emit(str(p))

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        src = Path(event.src_path)
        dst = Path(event.dest_path)
        if src.suffix.lower() in _MEDIA_EXTS or dst.suffix.lower() in _MEDIA_EXTS:
            log.debug("[Watcher] Moved: %s -> %s", src, dst)
            self._bridge.file_moved.emit(str(src), str(dst))


class WatcherService(QObject):
    """Manages watchdog observers for all enabled library directories."""

    file_added   = Signal(str)
    file_removed = Signal(str)
    file_moved   = Signal(str, str)
    sub_added    = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._observers: dict[str, Observer] = {}  # path -> Observer
        self._bridge    = _EventBridge()
        # Wire bridge -> self so callers only connect to WatcherService
        self._bridge.file_added.connect(self.file_added)
        self._bridge.file_removed.connect(self.file_removed)
        self._bridge.file_moved.connect(self.file_moved)
        self._bridge.sub_added.connect(self.sub_added)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_all(self) -> None:
        """Watch all enabled directories from the DB."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT path FROM directories WHERE is_enabled=1"
            ).fetchall()
        for row in rows:
            self.watch(row["path"])

    def stop_all(self) -> None:
        for path in list(self._observers):
            self._stop_observer(path)

    def watch(self, directory: str) -> None:
        """Start watching *directory* if not already watched."""
        if directory in self._observers:
            return
        if not Path(directory).is_dir():
            log.warning("[Watcher] Not a directory, skipping: %s", directory)
            return
        observer = Observer()
        observer.schedule(_MediaHandler(self._bridge), directory, recursive=True)
        observer.start()
        self._observers[directory] = observer
        log.info("[Watcher] Watching: %s", directory)

    def unwatch(self, directory: str) -> None:
        self._stop_observer(directory)

    # ------------------------------------------------------------------
    # Auto-integration slot: call when file_added fires
    # ------------------------------------------------------------------

    def handle_new_file(self, file_path: str) -> None:
        """Trigger a minimal scan_service upsert for the single new file."""
        try:
            from mlm.services.scan_service import ScanService
            from mlm.db.connection import get_connection as gc
            p = Path(file_path)
            with gc() as conn:
                row = conn.execute(
                    "SELECT id FROM directories WHERE ? LIKE path || '%'",
                    (file_path,),
                ).fetchone()
            if not row:
                log.warning("[Watcher] No directory record for '%s'", file_path)
                return
            ScanService().save_file_record(row["id"], p)
            log.info("[Watcher] Upserted new file record: %s", file_path)
        except Exception as exc:  # noqa: BLE001
            log.error("[Watcher] handle_new_file failed for '%s': %s", file_path, exc)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _stop_observer(self, path: str) -> None:
        obs = self._observers.pop(path, None)
        if obs:
            obs.stop()
            obs.join(timeout=3)
            log.info("[Watcher] Stopped watching: %s", path)
