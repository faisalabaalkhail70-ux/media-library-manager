from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QComboBox, QPushButton, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from mlm.db.connection import get_connection


class ShowDetailView(QWidget):
    def __init__(self, entity_id: int, show_title: str) -> None:
        super().__init__()
        self.entity_id = entity_id
        self.show_title = show_title
        self._all_episodes: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # ── Header ────────────────────────────────────────────────
        header = QHBoxLayout()
        title_lbl = QLabel(show_title)
        title_lbl.setObjectName("h1")
        header.addWidget(title_lbl)
        header.addStretch()

        self.season_combo = QComboBox()
        self.season_combo.addItem("All Seasons")
        self.season_combo.currentIndexChanged.connect(self._apply_filter)
        header.addWidget(QLabel("Season:"))
        header.addWidget(self.season_combo)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._load_episodes)
        header.addWidget(self.refresh_btn)

        layout.addLayout(header)

        # ── Status ────────────────────────────────────────────────
        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")
        layout.addWidget(self.status_label)

        # ── Table ─────────────────────────────────────────────────
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
        layout.addWidget(self.table)

        self._load_episodes()

    def _load_episodes(self) -> None:
        with get_connection() as conn:
            rows = conn.execute(
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

        self._all_episodes = [dict(r) for r in rows]

        # rebuild season combo
        seasons = sorted({r["season_number"] for r in self._all_episodes})
        self.season_combo.blockSignals(True)
        current_text = self.season_combo.currentText()
        self.season_combo.clear()
        self.season_combo.addItem("All Seasons")
        for s in seasons:
            self.season_combo.addItem(f"Season {s}", s)
        # restore selection if possible
        idx = self.season_combo.findText(current_text)
        self.season_combo.setCurrentIndex(max(idx, 0))
        self.season_combo.blockSignals(False)

        self._apply_filter()

    def _apply_filter(self) -> None:
        season_data = self.season_combo.currentData()
        if season_data is not None:
            episodes = [e for e in self._all_episodes if e["season_number"] == season_data]
        else:
            episodes = self._all_episodes

        self.table.setRowCount(0)
        for ep in episodes:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)

            is_missing = bool(ep["is_missing"])
            status_text = "❌ Missing" if is_missing else "✅ Available"
            color = QColor("#ef9a9a") if is_missing else QColor("#81c784")

            cells = [
                str(ep["season_number"]),
                str(ep["episode_number"]),
                ep["episode_title"] or "",
                ep["air_date"] or "",
                status_text,
                ep["file_name"] or "",
            ]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setForeground(color if col == 4 else QColor("#e0e0e0"))
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table.setItem(row_idx, col, item)

        # ── Status summary ────────────────────────────────────────
        total = len(episodes)
        missing = sum(1 for e in episodes if e["is_missing"])
        have = total - missing
        pct = round(have / total * 100) if total else 0
        self.status_label.setText(
            f"{total} episodes — {have} available  {missing} missing  ({pct}% complete)"
        )