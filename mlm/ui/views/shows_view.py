import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QTableView, QLineEdit, QAbstractItemView, QStackedWidget
)
from PySide6.QtCore import Qt, QSortFilterProxyModel
from mlm.db.connection import get_connection
from mlm.ui.models.shows_model import ShowsTableModel
from mlm.ui.column_visibility import ColumnVisibilityDialog, apply_saved_visibility
from mlm.ui.filter_panel import FilterPanel
from mlm.ui.grid_view import PosterGridWidget
from mlm.ui.views.entity_detail_panel import EntityDetailPanel
from mlm.workers.episode_worker import EpisodeWorker


class ShowsView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._all_rows: list[dict] = []
        self._source_model = ShowsTableModel([])
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._source_model)
        self._proxy.setSortCaseSensitivity(Qt.CaseInsensitive)
        self._detail_view = None
        self._entity_detail: EntityDetailPanel | None = None
        self._worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title_lbl = QLabel("TV Shows")
        title_lbl.setObjectName("h1")
        layout.addWidget(title_lbl)

        # ── Toolbar ─────────────────────────────────────────────────
        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by title...")
        self.search_input.setFixedWidth(300)
        self.search_input.textChanged.connect(self._apply_all)

        self.clear_search_btn = QPushButton("Clear")
        self.clear_search_btn.clicked.connect(self.search_input.clear)

        self.check_btn = QPushButton("Check Missing Episodes")
        self.check_btn.setObjectName("primary")
        self.check_btn.clicked.connect(self._check_missing)

        col_btn = QPushButton("\u2699 Columns")
        col_btn.clicked.connect(self._open_col_dialog)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_rows)

        # View toggle
        self._view_toggle = QPushButton("\u22f9 Grid View")
        self._view_toggle.setCheckable(True)
        self._view_toggle.clicked.connect(self._toggle_view)

        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")

        toolbar.addWidget(self.search_input)
        toolbar.addWidget(self.clear_search_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.status_label)
        toolbar.addWidget(self._view_toggle)
        toolbar.addWidget(self.check_btn)
        toolbar.addWidget(col_btn)
        toolbar.addWidget(self.refresh_btn)
        layout.addLayout(toolbar)

        # ── Filter panel ────────────────────────────────────────────
        self._filters = FilterPanel(media_type="show")
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
        self.table.doubleClicked.connect(self._open_episode_detail)
        self._stack.addWidget(self.table)   # index 0

        # Grid page (index 1)
        self._grid = PosterGridWidget()
        self._grid.card_clicked.connect(self._open_entity_detail)
        self._stack.addWidget(self._grid)   # index 1

        layout.addWidget(self._stack)

        hint = QLabel("Double-click a show (list) or click a card (grid) to view details.")
        hint.setObjectName("muted")
        layout.addWidget(hint)

        self.load_rows()
        apply_saved_visibility(self.table, "shows")

    def load_rows(self) -> None:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    me.id AS entity_id,
                    me.title, me.release_year, me.rating, me.genres_json, me.poster_path,
                    COUNT(DISTINCT CASE WHEN ep.is_missing = 0
                          THEN ep.season_number END)                            AS seasons_have,
                    COUNT(DISTINCT CASE
                        WHEN ep.is_missing = 1
                         AND ep.season_number NOT IN (
                             SELECT season_number FROM episodes e2
                             WHERE e2.entity_id = me.id AND e2.is_missing = 0
                         )
                        THEN ep.season_number END)                             AS seasons_missing,
                    SUM(CASE WHEN ep.is_missing = 0 THEN 1 ELSE 0 END)        AS episodes_have,
                    SUM(CASE WHEN ep.is_missing = 1 THEN 1 ELSE 0 END)        AS episodes_missing
                FROM media_entities me
                LEFT JOIN episodes ep ON ep.entity_id = me.id
                WHERE me.media_type = 'show'
                GROUP BY me.id
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
        self.status_label.setText(f"{len(rows)} of {len(self._all_rows)} shows")

    def _toggle_view(self) -> None:
        is_grid = self._view_toggle.isChecked()
        self._stack.setCurrentIndex(1 if is_grid else 0)
        self._view_toggle.setText("\u2630 List View" if is_grid else "\u22f9 Grid View")

    def _open_entity_detail(self, entity_id: int) -> None:
        self._entity_detail = EntityDetailPanel(entity_id, parent=self)
        self._entity_detail.show()

    def _check_missing(self) -> None:
        if self._worker and self._worker.isRunning():
            return
        self.check_btn.setEnabled(False)
        self.status_label.setText("Checking missing episodes via TMDB...")
        self._worker = EpisodeWorker()
        self._worker.finished_check.connect(self._on_check_done)
        self._worker.failed.connect(self._on_check_failed)
        main_win = self.window()
        if hasattr(main_win, "track_worker"):
            main_win.track_worker(self._worker, "Checking missing episodes…")
        self._worker.start()

    def _on_check_done(self, results: list) -> None:
        self.check_btn.setEnabled(True)
        total_missing = sum(r.get("missing_count", 0) for r in results)
        self.status_label.setText(
            f"Check complete — {total_missing} missing episode(s) across {len(results)} show(s)"
        )
        self.load_rows()

    def _on_check_failed(self, message: str) -> None:
        self.check_btn.setEnabled(True)
        self.status_label.setText(f"Check failed: {message}")

    def _open_col_dialog(self) -> None:
        dlg = ColumnVisibilityDialog(self.table, "shows", parent=self)
        dlg.exec()

    def _open_episode_detail(self, index) -> None:
        source_index = self._proxy.mapToSource(index)
        row = self._source_model.get_row(source_index.row())
        entity_id  = row.get("entity_id")
        show_title = row.get("title", "Show")
        if not entity_id:
            return
        from mlm.ui.views.show_detail_view import ShowDetailView
        self._detail_view = ShowDetailView(entity_id=entity_id, show_title=show_title)
        self._detail_view.setWindowTitle(f"Episodes — {show_title}")
        self._detail_view.resize(960, 640)
        self._detail_view.show()
