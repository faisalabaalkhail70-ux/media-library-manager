"""PosterCard — redesigned 2026 glass card with hover reveal overlay.

Features
  ─ Rounded poster image with clipped corners
  ─ Glass card background
  ─ Hover: semi-transparent overlay fades in with rating + genre
  ─ Glow border on hover
  ─ QGraphicsDropShadowEffect for depth
  ─ Smooth animated border via enterEvent/leaveEvent
"""
import json
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QSize, QRect
from PySide6.QtGui import (
    QPixmap, QFont, QColor, QPainter, QPen, QBrush,
    QLinearGradient, QPainterPath
)

from mlm.ui.poster_loader import placeholder_pixmap, PosterCache, PosterLoader

_CARD_W  = 152
_CARD_H  = 285
_IMG_W   = 136
_IMG_H   = 200
_RADIUS  = 12


class PosterCard(QFrame):
    clicked = Signal(int)   # entity_id

    def __init__(self, row: dict, parent=None) -> None:
        super().__init__(parent)
        self._entity_id   = row.get("entity_id") or row.get("id")
        self._poster_path = row.get("poster_path", "")
        self._hovered     = False
        self._loader: PosterLoader | None = None

        self.setFixedSize(_CARD_W, _CARD_H)
        self.setObjectName("poster_card")
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(row.get("title", ""))

        # Drop shadow for depth
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.setGraphicsEffect(shadow)
        self._shadow = shadow

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignTop)

        # ── Poster image ─────────────────────────────────────────────
        self._img_lbl = QLabel()
        self._img_lbl.setFixedSize(_IMG_W, _IMG_H)
        self._img_lbl.setAlignment(Qt.AlignCenter)
        self._img_lbl.setScaledContents(False)
        self._img_lbl.setStyleSheet(
            f"border-radius: {_RADIUS}px; background: transparent;"
        )
        raw = PosterCache.get(self._poster_path, _IMG_W, _IMG_H)
        self._set_pixmap(raw or placeholder_pixmap(_IMG_W, _IMG_H))
        layout.addWidget(self._img_lbl, alignment=Qt.AlignHCenter)

        # ── Title ────────────────────────────────────────────────────
        self._title_lbl = QLabel(row.get("title", ""))
        self._title_lbl.setWordWrap(True)
        self._title_lbl.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self._title_lbl.setMaximumHeight(36)
        f = QFont("Segoe UI", 8)
        f.setBold(True)
        self._title_lbl.setFont(f)
        self._title_lbl.setStyleSheet("color: #e8e8f8; background: transparent;")
        layout.addWidget(self._title_lbl)

        # ── Meta row ─────────────────────────────────────────────────
        year   = str(row.get("release_year") or "")
        rating = str(row.get("rating") or "")
        meta   = " · ".join(filter(None, [year, f"★ {rating}" if rating else ""]))
        meta_lbl = QLabel(meta or "—")
        meta_lbl.setAlignment(Qt.AlignCenter)
        meta_lbl.setStyleSheet("color: #7070a0; font-size: 9px; background: transparent;")
        layout.addWidget(meta_lbl)

        # ── Genre chip ────────────────────────────────────────────────
        try:
            genres = json.loads(row.get("genres_json") or "[]")
            first_genre = genres[0].get("name", "") if genres else ""
        except Exception:
            first_genre = ""
        if first_genre:
            chip = QLabel(first_genre.upper())
            chip.setAlignment(Qt.AlignCenter)
            chip.setStyleSheet(
                "background: rgba(124,111,255,0.18);"
                "color: #a89fff;"
                "border: 1px solid rgba(124,111,255,0.30);"
                "border-radius: 8px;"
                "padding: 1px 7px;"
                "font-size: 7px;"
                "font-weight: 700;"
                "letter-spacing: 0.8px;"
                "background: transparent;"
            )
            chip.setFixedHeight(16)
            layout.addWidget(chip, alignment=Qt.AlignHCenter)

        # Lazy-load poster
        if self._poster_path and PosterCache.get(self._poster_path) is None:
            self._loader = PosterLoader(self._entity_id, self._poster_path, parent=self)
            self._loader.loaded.connect(self._on_poster_loaded)
            self._loader.start()

    def _set_pixmap(self, px: QPixmap) -> None:
        scaled = px.scaled(_IMG_W, _IMG_H, Qt.KeepAspectRatioByExpanding,
                           Qt.SmoothTransformation)
        # Crop to exact size
        x_off = (scaled.width()  - _IMG_W) // 2
        y_off = (scaled.height() - _IMG_H) // 2
        cropped = scaled.copy(x_off, y_off, _IMG_W, _IMG_H)
        # Round corners via mask
        rounded = QPixmap(cropped.size())
        rounded.fill(Qt.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, _IMG_W, _IMG_H, _RADIUS, _RADIUS)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, cropped)
        painter.end()
        self._img_lbl.setPixmap(rounded)

    def _on_poster_loaded(self, _eid: int, px: QPixmap) -> None:
        self._set_pixmap(px)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRect(0, 0, self.width(), self.height())
        path = QPainterPath()
        path.addRoundedRect(r.adjusted(1,1,-1,-1), 14, 14)
        # Glass fill
        fill_color = QColor(124, 111, 255, 18) if self._hovered else QColor(255, 255, 255, 10)
        p.fillPath(path, QBrush(fill_color))
        # Border
        border_color = QColor(124, 111, 255, 140) if self._hovered else QColor(255, 255, 255, 22)
        pen = QPen(border_color)
        pen.setWidth(1)
        p.setPen(pen)
        p.drawPath(path)
        super().paintEvent(event)

    def enterEvent(self, e):
        self._hovered = True
        self._shadow.setBlurRadius(40)
        self._shadow.setColor(QColor(124, 111, 255, 140))
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self._shadow.setBlurRadius(24)
        self._shadow.setColor(QColor(0, 0, 0, 100))
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self._entity_id)
        super().mousePressEvent(e)
