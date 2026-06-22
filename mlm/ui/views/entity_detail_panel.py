"""Entity detail panel — shown when the user clicks a poster card or table row.

Displays:
  • Large poster (left)
  • Title, year, rating, genres, plot (right)
  • File info (path, size, codec, resolution)
  • “Add to Watchlist” / “Add to Collection” quick-actions

Opens as a floating, non-modal QDialog so the user can keep browsing.
"""
import json
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QWidget, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont

from mlm.app.paths import POSTER_DIR
from mlm.ui.poster_loader import PosterCache, PosterLoader, placeholder_pixmap
from mlm.db.connection import get_connection
from mlm.db.repositories.watchlist_repo import WatchlistRepository
from mlm.db.repositories.collections_repo import CollectionsRepository

_POSTER_W = 180
_POSTER_H = 267


class EntityDetailPanel(QDialog):
    def __init__(self, entity_id: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setMinimumSize(680, 400)
        self._entity_id = entity_id
        self._loader: PosterLoader | None = None
        self._wl_repo   = WatchlistRepository()
        self._col_repo  = CollectionsRepository()

        row = self._fetch(entity_id)
        if not row:
            QLabel("Entity not found.", parent=self)
            return

        self.setWindowTitle(row.get("title", "Detail"))

        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(20)

        # ── Left: poster ───────────────────────────────────────────
        left = QVBoxLayout()
        self._poster_lbl = QLabel()
        self._poster_lbl.setFixedSize(_POSTER_W, _POSTER_H)
        self._poster_lbl.setAlignment(Qt.AlignCenter)
        cached = PosterCache.get(row.get("poster_path"), _POSTER_W, _POSTER_H)
        self._poster_lbl.setPixmap(cached or placeholder_pixmap(_POSTER_W, _POSTER_H))
        left.addWidget(self._poster_lbl)
        left.addStretch()
        outer.addLayout(left)

        if row.get("poster_path") and cached is None:
            self._loader = PosterLoader(entity_id, row["poster_path"], parent=self)
            self._loader.loaded.connect(self._on_poster)
            self._loader.start()

        # ── Right: meta + actions ─────────────────────────────────
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_widget = QWidget()
        right = QVBoxLayout(right_widget)
        right.setSpacing(10)
        right_scroll.setWidget(right_widget)
        outer.addWidget(right_scroll, 1)

        def _h1(text):
            l = QLabel(text)
            f = QFont(); f.setPointSize(16); f.setBold(True)
            l.setFont(f); l.setWordWrap(True)
            return l

        def _muted(text):
            l = QLabel(text); l.setObjectName("muted")
            l.setWordWrap(True); return l

        right.addWidget(_h1(row.get("title", "")))

        # Year | Type | Rating
        year   = str(row.get("release_year") or "")
        mtype  = row.get("media_type", "").capitalize()
        rating = str(row.get("rating") or "")
        meta   = "  •  ".join(filter(None, [year, mtype, f"★ {rating}" if rating else ""]))
        right.addWidget(_muted(meta))

        # Genres
        try:
            genres = json.loads(row.get("genres_json") or "[]")
            genre_str = ", ".join(g.get("name", "") for g in genres)
        except Exception:
            genre_str = ""
        if genre_str:
            right.addWidget(_muted(f"Genres: {genre_str}"))

        # Plot
        plot = row.get("plot", "") or ""
        if plot:
            right.addWidget(QLabel("Overview"))
            plot_lbl = QLabel(plot)
            plot_lbl.setWordWrap(True)
            plot_lbl.setObjectName("muted")
            right.addWidget(plot_lbl)

        # File info
        files = self._fetch_files(entity_id)
        if files:
            right.addWidget(QLabel("Files"))
            for f in files[:5]:
                size_mb = round((f.get("file_size_bytes") or 0) / (1024**2), 1)
                codec   = f.get("video_codec") or ""
                res     = f.get("resolution") or ""
                line    = f"{f.get('file_name','')}  —  {size_mb} MB  {res}  {codec}"
                right.addWidget(_muted(line))

        # Divider
        div = QFrame(); div.setFrameShape(QFrame.HLine)
        right.addWidget(div)

        # Quick actions
        right.addWidget(QLabel("Quick Actions"))
        actions_row = QHBoxLayout()

        wl_btn = QPushButton(
            "\u2713 On Watchlist" if self._wl_repo.is_on_watchlist(entity_id)
            else "+ Add to Watchlist"
        )
        wl_btn.clicked.connect(lambda: self._add_to_watchlist(wl_btn))
        actions_row.addWidget(wl_btn)

        cols = self._col_repo.list_collections()
        if cols:
            col_combo = QComboBox()
            col_combo.addItem("Add to collection…")
            for c in cols:
                col_combo.addItem(c["name"], c["id"])
            col_btn = QPushButton("Add")
            col_btn.clicked.connect(lambda: self._add_to_collection(col_combo))
            actions_row.addWidget(col_combo)
            actions_row.addWidget(col_btn)

        actions_row.addStretch()
        right.addLayout(actions_row)
        right.addStretch()

    # ── DB helpers ─────────────────────────────────────────────

    @staticmethod
    def _fetch(entity_id: int) -> dict | None:
        with get_connection() as conn:
            r = conn.execute(
                "SELECT * FROM media_entities WHERE id = ?", (entity_id,)
            ).fetchone()
        return dict(r) if r else None

    @staticmethod
    def _fetch_files(entity_id: int) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT file_name, file_size_bytes, resolution, video_codec
                FROM media_files
                WHERE entity_id = ? AND removed_at IS NULL
                LIMIT 10
                """,
                (entity_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Slots ─────────────────────────────────────────────────

    def _on_poster(self, _eid: int, px: QPixmap) -> None:
        self._poster_lbl.setPixmap(
            px.scaled(_POSTER_W, _POSTER_H, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def _add_to_watchlist(self, btn: QPushButton) -> None:
        if self._wl_repo.is_on_watchlist(self._entity_id):
            return
        self._wl_repo.add(self._entity_id)
        btn.setText("\u2713 On Watchlist")
        btn.setEnabled(False)

    def _add_to_collection(self, combo: QComboBox) -> None:
        col_id = combo.currentData()
        if col_id is None:
            QMessageBox.information(self, "Select collection", "Pick a collection first.")
            return
        self._col_repo.add_item(col_id, self._entity_id)
        QMessageBox.information(self, "Added", f"Added to \u201c{combo.currentText()}\u201d.")
