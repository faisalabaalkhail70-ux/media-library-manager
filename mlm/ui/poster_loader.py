"""Async poster loader.

Downloads TMDB poster images to POSTER_DIR in a background QThread and
emits ``loaded(entity_id, QPixmap)`` when done.  If the file is already
cached it returns immediately (no network call).

TMDB image base URL: https://image.tmdb.org/t/p/w185<poster_path>
"""
from pathlib import Path
from PySide6.QtCore import QThread, Signal, QObject
from PySide6.QtGui import QPixmap
from mlm.app.paths import POSTER_DIR

_TMDB_BASE = "https://image.tmdb.org/t/p/w185"
_PLACEHOLDER: QPixmap | None = None


def placeholder_pixmap(w: int = 120, h: int = 178) -> QPixmap:
    """Return a grey placeholder pixmap (created once, cached)."""
    global _PLACEHOLDER
    if _PLACEHOLDER is None or _PLACEHOLDER.width() != w:
        from PySide6.QtGui import QPainter, QColor, QFont
        from PySide6.QtCore import Qt
        px = QPixmap(w, h)
        px.fill(QColor("#2a2a3e"))
        p = QPainter(px)
        p.setPen(QColor("#555"))
        f = QFont()
        f.setPointSize(9)
        p.setFont(f)
        p.drawText(px.rect(), Qt.AlignCenter, "No Poster")
        p.end()
        _PLACEHOLDER = px
    return _PLACEHOLDER


class PosterLoader(QThread):
    """Worker thread that downloads one poster and emits loaded()."""
    loaded = Signal(int, QPixmap)   # (entity_id, pixmap)

    def __init__(self, entity_id: int, poster_path: str, parent: QObject | None = None):
        super().__init__(parent)
        self._entity_id  = entity_id
        self._poster_path = poster_path

    def run(self) -> None:
        if not self._poster_path:
            return
        safe  = self._poster_path.replace("/", "_").lstrip("_")
        local = POSTER_DIR / safe
        if not local.exists():
            try:
                import urllib.request
                url = _TMDB_BASE + self._poster_path
                urllib.request.urlretrieve(url, local)
            except Exception:
                return
        px = QPixmap(str(local))
        if not px.isNull():
            self.loaded.emit(self._entity_id, px)


class PosterCache:
    """Thin synchronous cache — returns cached pixmap or None."""

    @staticmethod
    def get(poster_path: str | None, w: int = 120, h: int = 178) -> QPixmap | None:
        if not poster_path:
            return None
        safe  = poster_path.replace("/", "_").lstrip("_")
        local = POSTER_DIR / safe
        if local.exists():
            px = QPixmap(str(local))
            if not px.isNull():
                return px.scaled(w, h, aspectMode=__import__(
                    'PySide6.QtCore', fromlist=['Qt']).Qt.KeepAspectRatio,
                    transformMode=__import__(
                    'PySide6.QtCore', fromlist=['Qt']).Qt.SmoothTransformation)
        return None
