"""PosterCard widget — a single card in the grid view.

Shows:
  ─ poster image (120×178) or placeholder
  ─ title (elided, max 2 lines)
  ─ year  |  rating
  ─ genre chip (first genre only)

Clicking emits ``clicked(entity_id)``.
Hovering shows a subtle highlight border.
"""
import json
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QFont, QColor, QPainter, QPen

from mlm.ui.poster_loader import placeholder_pixmap, PosterCache, PosterLoader

_CARD_W = 148
_CARD_H = 270
_IMG_W  = 120
_IMG_H  = 178


class PosterCard(QFrame):
    clicked = Signal(int)   # entity_id

    def __init__(self, row: dict, parent=None) -> None:
        super().__init__(parent)
        self._entity_id  = row.get("entity_id") or row.get("id")
        self._poster_path = row.get("poster_path", "")
        self._loader: PosterLoader | None = None

        self.setFixedSize(_CARD_W, _CARD_H)
        self.setObjectName("poster_card")
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(row.get("title", ""))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignTop)

        # ── Poster image ──────────────────────────────────────────
        self._img_lbl = QLabel()
        self._img_lbl.setFixedSize(_IMG_W, _IMG_H)
        self._img_lbl.setAlignment(Qt.AlignCenter)
        self._img_lbl.setScaledContents(False)
        self._set_pixmap(PosterCache.get(self._poster_path, _IMG_W, _IMG_H)
                         or placeholder_pixmap(_IMG_W, _IMG_H))
        layout.addWidget(self._img_lbl, alignment=Qt.AlignHCenter)

        # ── Title ────────────────────────────────────────────────
        self._title_lbl = QLabel(row.get("title", ""))
        self._title_lbl.setWordWrap(True)
        self._title_lbl.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self._title_lbl.setMaximumHeight(38)
        f = QFont()
        f.setPointSize(8)
        f.setBold(True)
        self._title_lbl.setFont(f)
        self._title_lbl.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(self._title_lbl)

        # ── Meta row (year | rating) ───────────────────────────────
        year   = str(row.get("release_year") or "")
        rating = str(row.get("rating") or "")
        meta   = " | ".join(filter(None, [year, f"★ {rating}" if rating else ""]))
        meta_lbl = QLabel(meta or "—")
        meta_lbl.setAlignment(Qt.AlignCenter)
        meta_lbl.setStyleSheet("color: #888; font-size: 9px;")
        layout.addWidget(meta_lbl)

        # ── Genre chip ─────────────────────────────────────────────
        try:
            genres = json.loads(row.get("genres_json") or "[]")
            first_genre = genres[0].get("name", "") if genres else ""
        except Exception:
            first_genre = ""
        if first_genre:
            chip = QLabel(first_genre)
            chip.setAlignment(Qt.AlignCenter)
            chip.setStyleSheet(
                "background:#1e3a5f; color:#90caf9; border-radius:8px;"
                "padding:1px 6px; font-size:8px;"
            )
            chip.setFixedHeight(16)
            layout.addWidget(chip, alignment=Qt.AlignHCenter)

        # Lazy-load poster from TMDB if not cached
        if self._poster_path and PosterCache.get(self._poster_path) is None:
            self._loader = PosterLoader(self._entity_id, self._poster_path, parent=self)
            self._loader.loaded.connect(self._on_poster_loaded)
            self._loader.start()

    def _set_pixmap(self, px: QPixmap) -> None:
        self._img_lbl.setPixmap(
            px.scaled(_IMG_W, _IMG_H, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def _on_poster_loaded(self, _entity_id: int, px: QPixmap) -> None:
        self._set_pixmap(px)

    # ── Events ─────────────────────────────────────────────────
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._entity_id)
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:
        self.setStyleSheet("#poster_card { border: 2px solid #6c63ff; border-radius: 8px; }")
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.setStyleSheet("")
        super().leaveEvent(event)
