"""Show detail window: season summary cards + full episode list.

Opened by double-clicking a show in ShowsView.
Displays:
  - One summary card per season: total / have / missing / completion %
  - A filterable episode table: Season | Episode | Title | Air Date | Status | File
Rows are colour-coded: green = on disk, red = missing.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QComboBox, QPushButton, QHeaderView,
    QFrame, QGridLayout, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from mlm.db.connection import get_connection


# ── Season summary card ───────────────────────────────────────────────────────

class SeasonCard(QFrame):
    """A compact card showing per-season stats."""

    def __init__(
        self,
        season: int,
        total: int,
        have: int,
        missing: int,
    ) -> None:
        super().__init__()
        self.setObjectName("stat_card")
        self.setFixedWidth(150)

        pct = round(have / total * 100) if total else 0
        color = "#81c784" if pct == 100 else ("#fff176" if pct >= 50 else "#ef9a9a")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)

        season_lbl = QLabel(f"Season {season}")
        season_lbl.setObjectName("panel_title")
        layout.addWidget(season_lbl)

        have_lbl = QLabel(f"✅ Have: {have}")
        have_lbl.setStyleSheet("color: #81c784; font-size: 12px;")
        layout.addWidget(have_lbl)

        missing_lbl = QLabel(f"❌ Missing: {missing}")
        missing_lbl.setStyleSheet("color: #ef9a9a; font-size: 12px;")
        layout.addWidget(missing_lbl)

        pct_lbl = QLabel(f"{pct}% complete")
        pct_lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
        layout.addWidget(pct_lbl)


# ── Main detail window ────────────────────────────────────────────────────────

class ShowDetailView(QWidget):
    def __init__(self, entity_id: int, show_title: str) -> None:
        super().__init__()
        self.entity_id = entity_id
        self.show_title = show_title
        self._all_episodes: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # ── Header row ────────────────────────────────────────────
        header = QHBoxLayout()
        title_lbl = QLabel(show_title)
        title_lbl.setObjectName("h1")
        header.addWidget(title_lbl)
        header.addStretch()

        self.season_combo = QComboBox()
        self.season_combo.addItem("All Seasons")
        self.season_combo.currentIndexChanged.connect(self._apply_filter)
        header.addWidget(QLabel("Filter:"))
        header.addWidget(self.season_combo)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._load_episodes)
        header.addWidget(self.refresh_btn)
        layout.addLayout(header)

        # ── Season summary cards (scrollable row) ─────────────────
        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setFixedHeight(120)
        self.cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.cards_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.cards_scroll.setFrameShape(QFrame.NoFrame)

        self.cards_container = QWidget()
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch()
        self.cards_scroll.setWidget(self.cards_container)
        layout.addWidget(self.cards_scroll)

        # ── Status bar ────────────────────────────────────────────
        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")
        layout.addWidget(self.status_label)

        # ── Episode table ─────────────────────────────────────────
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Season", "Episode", "Title", "Air Date", "Status", "File"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        self._load_episodes()

    # ── Data loading ──────────────────────────────────────────────

    def _load_episodes(self) -> None:
        """Load all episode rows for this show.

        Combines:
        1. Rows from the `episodes` table (both present and missing).
        2. media_files rows with season/episode parsed but not yet
           in the episodes table — shown as \u2705 Available with their filename.
        """
        with get_connection() as conn:
            # Linked episodes (from episodes table)
            linked = conn.execute(
                """
                SELECT
                    ep.season_number,
                    ep.episode_number,
                    ep.episode_title,
                    ep.air_date,
                    ep.is_missing,
                    mf.file_name
                FROM episodes ep
                LEFT JOIN media_files mf ON mf.id = ep.media_file_id
                WHERE ep.entity_id = ?
                ORDER BY ep.season_number, ep.episode_number
                """,
                (self.entity_id,),
            ).fetchall()

            # Unlinked files on disk (season/episode parsed, not in episodes)
            unlinked = conn.execute(
                """
                SELECT
                    mf.season_number,
                    mf.episode_number,
                    NULL        AS episode_title,
                    NULL        AS air_date,
                    0           AS is_missing,
                    mf.file_name
                FROM media_files mf
                WHERE mf.entity_id = ?
                  AND mf.removed_at IS NULL
                  AND mf.season_number IS NOT NULL
                  AND mf.episode_number IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM episodes ep
                      WHERE ep.entity_id = mf.entity_id
                        AND ep.season_number = mf.season_number
                        AND ep.episode_number = mf.episode_number
                  )
                ORDER BY mf.season_number, mf.episode_number
                """,
                (self.entity_id,),
            ).fetchall()

        self._all_episodes = [dict(r) for r in linked] + [dict(r) for r in unlinked]
        self._all_episodes.sort(key=lambda r: (r["season_number"], r["episode_number"]))

        self._rebuild_season_combo()
        self._rebuild_season_cards()
        self._apply_filter()

    def _rebuild_season_combo(self) -> None:
        seasons = sorted({r["season_number"] for r in self._all_episodes})
        self.season_combo.blockSignals(True)
        current_text = self.season_combo.currentText()
        self.season_combo.clear()
        self.season_combo.addItem("All Seasons")
        for s in seasons:
            self.season_combo.addItem(f"Season {s}", s)
        idx = self.season_combo.findText(current_text)
        self.season_combo.setCurrentIndex(max(idx, 0))
        self.season_combo.blockSignals(False)

    def _rebuild_season_cards(self) -> None:
        """Replace season summary cards with fresh data."""
        # Clear existing cards (keep the trailing stretch)
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        seasons = sorted({r["season_number"] for r in self._all_episodes})
        for s in seasons:
            eps = [e for e in self._all_episodes if e["season_number"] == s]
            have    = sum(1 for e in eps if not e["is_missing"])
            missing = sum(1 for e in eps if e["is_missing"])
            total   = len(eps)
            card = SeasonCard(season=s, total=total, have=have, missing=missing)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

    # ── Filtering & table rendering ───────────────────────────────

    def _apply_filter(self) -> None:
        season_data = self.season_combo.currentData()
        episodes = (
            [e for e in self._all_episodes if e["season_number"] == season_data]
            if season_data is not None
            else self._all_episodes
        )

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for ep in episodes:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)

            is_missing = bool(ep["is_missing"])
            status_text = "❌ Missing" if is_missing else "✅ Available"
            row_color = QColor("#ef9a9a") if is_missing else QColor("#81c784")
            muted = QColor("#e0e0e0")

            cells = [
                (str(ep["season_number"]),   muted),
                (str(ep["episode_number"]),  muted),
                (ep["episode_title"] or "",  muted),
                (ep["air_date"] or "",        muted),
                (status_text,                 row_color),
                (ep["file_name"] or "",       muted),
            ]
            for col, (text, color) in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setForeground(color)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table.setItem(row_idx, col, item)

        self.table.setSortingEnabled(True)

        # ── Status bar summary ────────────────────────────────────
        total   = len(episodes)
        missing = sum(1 for e in episodes if e["is_missing"])
        have    = total - missing
        pct     = round(have / total * 100) if total else 0
        self.status_label.setText(
            f"{total} episodes  —  ✅ {have} available  ❌ {missing} missing  ({pct}% complete)"
        )
