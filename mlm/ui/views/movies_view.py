import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QTableView, QLineEdit, QAbstractItemView
)
from PySide6.QtCore import Qt, QSortFilterProxyModel
from mlm.db.connection import get_connection
from mlm.ui.models.movies_model import MoviesTableModel
from mlm.ui.column_visibility import ColumnVisibilityDialog, apply_saved_visibility


class MoviesView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._all_rows: list[dict] = []
        self._source_model = MoviesTableModel([])
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._source_model)
        self._proxy.setSortCaseSensitivity(Qt.CaseInsensitive)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Movies")
        title.setObjectName("h1")
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by title...")
        self.search_input.setFixedWidth(300)
        self.search_input.textChanged.connect(self._apply_filter)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.search_input.clear)

        col_btn = QPushButton("\u2699 Columns")
        col_btn.clicked.connect(self._open_col_dialog)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_rows)

        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")

        toolbar.addWidget(self.search_input)
        toolbar.addWidget(clear_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.status_label)
        toolbar.addWidget(col_btn)
        toolbar.addWidget(refresh_btn)
        layout.addLayout(toolbar)

        self.table = QTableView()
        self.table.setModel(self._proxy)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        layout.addWidget(self.table)

        self.load_rows()
        apply_saved_visibility(self.table, "movies")

    def load_rows(self) -> None:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT me.id AS entity_id, me.title, me.release_year,
                       me.rating, me.genres_json,
                       mf.resolution, mf.file_size_bytes, mf.file_name
                FROM media_entities me
                LEFT JOIN media_files mf ON mf.entity_id = me.id AND mf.removed_at IS NULL
                WHERE me.media_type = 'movie'
                ORDER BY me.title ASC
                """
            ).fetchall()

        result = []
        for r in rows:
            d = dict(r)
            try:
                genres = json.loads(d.get("genres_json") or "[]")
                d["genres"] = ", ".join(g.get("name", "") for g in genres)
            except Exception:
                d["genres"] = ""
            result.append(d)

        self._all_rows = result
        self._apply_filter()

    def _apply_filter(self) -> None:
        q = self.search_input.text().strip().lower()
        filtered = (
            [r for r in self._all_rows if q in r.get("title", "").lower()]
            if q else self._all_rows
        )
        self._source_model.set_rows(filtered)
        self.status_label.setText(f"{len(filtered)} of {len(self._all_rows)} movies")

    def _open_col_dialog(self) -> None:
        dlg = ColumnVisibilityDialog(self.table, "movies", parent=self)
        dlg.exec()
