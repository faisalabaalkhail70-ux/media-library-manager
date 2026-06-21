import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QTableView, QLineEdit, QAbstractItemView
)
from PySide6.QtCore import Qt
from mlm.db.connection import get_connection
from mlm.ui.models.shows_model import ShowsTableModel


class ShowsView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._all_rows: list[dict] = []
        self.model = ShowsTableModel([])
        self._detail_view = None  # lazy init

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("TV Shows")
        title.setObjectName("h1")
        layout.addWidget(title)

        # ── Toolbar ───────────────────────────────────────────────
        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by title...")
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
        self.table.doubleClicked.connect(self._open_detail)
        layout.addWidget(self.table)

        hint = QLabel("Double-click a show to view episode details.")
        hint.setObjectName("muted")
        layout.addWidget(hint)

        self.load_rows()

    def load_rows(self) -> None:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    me.id             AS entity_id,
                    me.title,
                    me.release_year,
                    me.rating,
                    me.genres_json    AS genres_json,
                    COUNT(DISTINCT ep.season_number)   AS seasons_count,
                    COUNT(ep.id)                       AS episodes_total,
                    SUM(CASE WHEN ep.is_missing = 0 THEN 1 ELSE 0 END) AS episodes_have,
                    SUM(CASE WHEN ep.is_missing = 1 THEN 1 ELSE 0 END) AS episodes_missing
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
            # flatten genres JSON → comma-separated string
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
        self.model.set_rows(filtered)
        self.status_label.setText(f"{len(filtered)} of {len(self._all_rows)} shows")

    def _clear_search(self) -> None:
        self.search_input.clear()

    def _open_detail(self, index) -> None:
        row = self.model.get_row(index.row())
        entity_id = row.get("entity_id")
        show_title = row.get("title", "Show")
        if not entity_id:
            return

        from mlm.ui.views.show_detail_view import ShowDetailView
        self._detail_view = ShowDetailView(entity_id=entity_id, show_title=show_title)
        self._detail_view.setWindowTitle(f"Episodes — {show_title}")
        self._detail_view.resize(900, 600)
        self._detail_view.show()