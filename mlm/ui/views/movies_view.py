from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QTableView, QLineEdit, QAbstractItemView
)
from PySide6.QtCore import Qt
from mlm.db.connection import get_connection
from mlm.ui.models.media_files_model import MediaFilesTableModel


class MoviesView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._all_rows: list[dict] = []
        self.model = MediaFilesTableModel([])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Movies")
        title.setObjectName("h1")
        layout.addWidget(title)

        # ── Toolbar ───────────────────────────────────────────────
        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by title or filename...")
        self.search_input.setFixedWidth(300)
        self.search_input.textChanged.connect(self._apply_filter)

        self.clear_search_btn = QPushButton("Clear")
        self.clear_search_btn.clicked.connect(self._clear_search)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_rows)

        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")

        toolbar.addWidget(self.search_input)
        toolbar.addWidget(self.clear_search_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.status_label)
        toolbar.addWidget(self.refresh_btn)
        layout.addLayout(toolbar)

        # ── Table ─────────────────────────────────────────────────
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSortingEnabled(False)
        layout.addWidget(self.table)

        self.load_rows()

    def load_rows(self) -> None:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    mf.id, mf.file_name, mf.file_path,
                    mf.file_size_bytes, mf.modified_at,
                    mf.resolution, mf.video_codec,
                    me.title AS matched_title, me.release_year
                FROM media_files mf
                JOIN media_entities me ON me.id = mf.entity_id
                WHERE me.media_type = 'movie' AND mf.removed_at IS NULL
                ORDER BY me.title ASC
                LIMIT 5000
                """
            ).fetchall()
        self._all_rows = [dict(r) for r in rows]
        self._apply_filter()

    def _apply_filter(self) -> None:
        q = self.search_input.text().strip().lower()
        if q:
            filtered = [
                r for r in self._all_rows
                if q in (r.get("matched_title") or "").lower()
                or q in (r.get("file_name") or "").lower()
            ]
        else:
            filtered = self._all_rows
        self.model.set_rows(filtered)
        self.status_label.setText(f"{len(filtered)} of {len(self._all_rows)} movies")

    def _clear_search(self) -> None:
        self.search_input.clear()