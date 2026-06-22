import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QTableView, QLineEdit, QAbstractItemView, QStackedWidget
)
from PySide6.QtCore import Qt, QSortFilterProxyModel
from mlm.db.connection import get_connection
from mlm.ui.models.movies_model import MoviesTableModel
from mlm.ui.column_visibility import ColumnVisibilityDialog, apply_saved_visibility
from mlm.ui.filter_panel import FilterPanel
from mlm.ui.grid_view import PosterGridWidget
from mlm.ui.views.entity_detail_panel import EntityDetailPanel


class MoviesView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._all_rows: list[dict] = []
        self._source_model = MoviesTableModel([])
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._source_model)
        self._proxy.setSortCaseSensitivity(Qt.CaseInsensitive)
        self._detail: EntityDetailPanel | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel("Movies")
        title.setObjectName("h1")
        layout.addWidget(title)

        # ── Toolbar ─────────────────────────────────────────────────
        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by title...")
        self.search_input.setFixedWidth(300)
        self.search_input.textChanged.connect(self._apply_all)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.search_input.clear)

        col_btn = QPushButton("\u2699 Columns")
        col_btn.clicked.connect(self._open_col_dialog)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_rows)

        # View toggle
        self._view_toggle = QPushButton("\u22f9 Grid View")
        self._view_toggle.setCheckable(True)
        self._view_toggle.clicked.connect(self._toggle_view)

        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")

        toolbar.addWidget(self.search_input)
        toolbar.addWidget(clear_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.status_label)
        toolbar.addWidget(self._view_toggle)
        toolbar.addWidget(col_btn)
        toolbar.addWidget(refresh_btn)
        layout.addLayout(toolbar)

        # ── Filter panel ────────────────────────────────────────────
        self._filters = FilterPanel(media_type="movie")
        self._filters.changed.connect(self._apply_all)
        layout.addWidget(self._filters)

        # ── Stacked: table | grid ─────────────────────────────────────
        self._stack = QStackedWidget()

        # Table page (index 0)
        self.table = QTableView()
        self.table.setModel(self._proxy)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.doubleClicked.connect(self._open_detail_from_table)
        self._stack.addWidget(self.table)   # index 0

        # Grid page (index 1)
        self._grid = PosterGridWidget()
        self._grid.card_clicked.connect(self._open_detail)
        self._stack.addWidget(self._grid)   # index 1

        layout.addWidget(self._stack)

        self.load_rows()
        apply_saved_visibility(self.table, "movies")

    def load_rows(self) -> None:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT me.id AS entity_id, me.title, me.release_year,
                       me.rating, me.genres_json, me.poster_path,
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
        self._filters.populate_genres(result)
        self._apply_all()

    def _apply_all(self) -> None:
        q = self.search_input.text().strip().lower()
        rows = self._all_rows
        if q:
            rows = [r for r in rows if q in r.get("title", "").lower()]
        rows = self._filters.apply(rows)
        self._source_model.set_rows(rows)
        self._grid.set_rows(rows)
        self.status_label.setText(f"{len(rows)} of {len(self._all_rows)} movies")

    def _toggle_view(self) -> None:
        is_grid = self._view_toggle.isChecked()
        self._stack.setCurrentIndex(1 if is_grid else 0)
        self._view_toggle.setText("\u2630 List View" if is_grid else "\u22f9 Grid View")

    def _open_detail(self, entity_id: int) -> None:
        self._detail = EntityDetailPanel(entity_id, parent=self)
        self._detail.show()

    def _open_detail_from_table(self, index) -> None:
        src = self._proxy.mapToSource(index)
        row = self._source_model._rows[src.row()]
        self._open_detail(row.get("entity_id"))

    def _open_col_dialog(self) -> None:
        dlg = ColumnVisibilityDialog(self.table, "movies", parent=self)
        dlg.exec()
