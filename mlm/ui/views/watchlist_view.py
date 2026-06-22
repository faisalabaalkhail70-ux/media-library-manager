"""Watchlist view — track movies & shows you plan to watch.

Features
--------
- Pending / Watched tabs
- Priority 1–10 (editable inline via spin box in dialog)
- Notes per entry
- Mark Watched / Unwatch buttons
- Add via search dialog (only shows entities not already on the list)
- Remove from list
- Export watchlist to CSV
"""
import json
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QAbstractItemView, QTabWidget, QDialog,
    QDialogButtonBox, QLineEdit, QListWidget, QListWidgetItem,
    QSpinBox, QTextEdit, QFormLayout, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QColor

from mlm.db.repositories.watchlist_repo import WatchlistRepository


# ── Shared palette
_GREEN   = QColor("#81c784")
_YELLOW  = QColor("#fff176")
_AMBER   = QColor("#ffa726")
_RED     = QColor("#ef9a9a")
_CYAN    = QColor("#4dd0e1")
_MUTED   = QColor("#6e6e8a")
_NORMAL  = QColor("#d0d0e8")
_WATCHED = QColor("#505060")   # dim grey for already-watched rows


def _rating_color(rating) -> QColor:
    try:
        r = float(rating)
    except (TypeError, ValueError):
        return _MUTED
    if r >= 7.0: return _GREEN
    if r >= 5.0: return _YELLOW
    return _RED


# ── Table model
class _WatchlistModel(QAbstractTableModel):
    HEADERS = ["Priority", "Title", "Type", "Year", "Rating", "Added", "Watched", "Notes"]
    _COL_PRIO    = 0
    _COL_TITLE   = 1
    _COL_TYPE    = 2
    _COL_YEAR    = 3
    _COL_RATING  = 4
    _COL_ADDED   = 5
    _COL_WATCHED = 6
    _COL_NOTES   = 7

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[dict] = []

    def set_rows(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def get_row(self, index: int) -> dict:
        return self._rows[index]

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        col = index.column()
        is_watched = bool(row.get("watched_at"))
        prio = row.get("priority", 5)

        if role == Qt.DisplayRole:
            if col == self._COL_PRIO:    return str(prio)
            if col == self._COL_TITLE:   return row.get("title", "")
            if col == self._COL_TYPE:    return row.get("media_type", "").capitalize()
            if col == self._COL_YEAR:    return str(row.get("release_year") or "")
            if col == self._COL_RATING:  return str(row.get("rating") or "")
            if col == self._COL_ADDED:   return str(row.get("added_at", ""))[:10]
            if col == self._COL_WATCHED:
                w = row.get("watched_at")
                return str(w)[:10] if w else "—"
            if col == self._COL_NOTES:   return row.get("notes", "") or ""

        if role == Qt.ForegroundRole:
            # Watched rows: everything dimmed to a single muted tone
            if is_watched:
                return _WATCHED

            # Priority column: traffic-light (1–3 urgent red, 4–6 amber, 7–10 green)
            if col == self._COL_PRIO:
                if prio <= 3: return _RED
                if prio <= 6: return _AMBER
                return _GREEN

            # Rating column: color by score
            if col == self._COL_RATING:
                return _rating_color(row.get("rating"))

            # Type: movie = blue, show = green, other = muted
            if col == self._COL_TYPE:
                mtype = (row.get("media_type") or "").lower()
                if mtype == "movie": return _CYAN
                if mtype == "show":  return _GREEN
                return _MUTED

            # Watched date: green tick-tone when filled
            if col == self._COL_WATCHED:
                return _GREEN if row.get("watched_at") else _MUTED

            # Year, Added, Notes: muted
            if col in (self._COL_YEAR, self._COL_ADDED, self._COL_NOTES):
                return _MUTED

            return _NORMAL

        if role == Qt.UserRole:
            return row.get("id")

        return None


# ── Add dialog
class _AddDialog(QDialog):
    def __init__(self, repo: WatchlistRepository, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add to Watchlist")
        self.setMinimumWidth(480)
        self._repo = repo
        self._entity_id: int | None = None

        lay = QVBoxLayout(self)
        lay.setSpacing(8)

        lay.addWidget(QLabel("Search for a movie or show:"))
        self._search = QLineEdit()
        self._search.setPlaceholderText("Type to search...")
        self._search.textChanged.connect(self._do_search)
        lay.addWidget(self._search)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._pick)
        lay.addWidget(self._list)

        form = QFormLayout()
        self._priority = QSpinBox()
        self._priority.setRange(1, 10)
        self._priority.setValue(5)
        self._priority.setToolTip("1 = highest priority, 10 = lowest")
        form.addRow("Priority (1–10):", self._priority)

        self._notes = QTextEdit()
        self._notes.setFixedHeight(60)
        self._notes.setPlaceholderText("Optional notes...")
        form.addRow("Notes:", self._notes)
        lay.addLayout(form)

        self._status = QLabel("")
        self._status.setObjectName("muted")
        lay.addWidget(self._status)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)
        self._search.setFocus()

    def _do_search(self, text: str) -> None:
        self._list.clear()
        if len(text.strip()) < 2:
            return
        results = self._repo.search_entities(text)
        for r in results:
            label = f"{r['title']}  ({r.get('release_year') or '?'})  [{r['media_type']}]"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, r["entity_id"])
            self._list.addItem(item)
        self._status.setText(f"{len(results)} result(s)")

    def _pick(self, item: QListWidgetItem) -> None:
        self._entity_id = item.data(Qt.UserRole)
        self.accept()

    def _on_accept(self) -> None:
        sel = self._list.currentItem()
        if sel and self._entity_id is None:
            self._entity_id = sel.data(Qt.UserRole)
        self.accept()

    @property
    def entity_id(self) -> int | None: return self._entity_id
    @property
    def priority(self) -> int: return self._priority.value()
    @property
    def notes(self) -> str: return self._notes.toPlainText().strip()


# ── Tab widget helper
def _make_table(model, proxy) -> QTableView:
    t = QTableView()
    t.setModel(proxy)
    proxy.setSourceModel(model)
    proxy.setSortCaseSensitivity(Qt.CaseInsensitive)
    t.horizontalHeader().setStretchLastSection(True)
    t.setAlternatingRowColors(True)
    t.verticalHeader().setVisible(False)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setSortingEnabled(True)
    return t


# ── Main view
class WatchlistView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._repo = WatchlistRepository()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(12)

        hdr = QHBoxLayout()
        title = QLabel("Watchlist")
        title.setObjectName("h1")
        hdr.addWidget(title)
        hdr.addStretch()
        self._count_lbl = QLabel("")
        self._count_lbl.setObjectName("muted")
        hdr.addWidget(self._count_lbl)
        outer.addLayout(hdr)

        toolbar = QHBoxLayout()
        add_btn = QPushButton("+ Add to Watchlist")
        add_btn.clicked.connect(self._add)
        self._watch_btn = QPushButton("✓ Mark Watched")
        self._watch_btn.clicked.connect(self._mark_watched)
        self._unwatch_btn = QPushButton("Unwatch")
        self._unwatch_btn.clicked.connect(self._mark_unwatched)
        self._remove_btn = QPushButton("Remove")
        self._remove_btn.clicked.connect(self._remove)
        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self._export_csv)
        toolbar.addWidget(add_btn)
        toolbar.addWidget(self._watch_btn)
        toolbar.addWidget(self._unwatch_btn)
        toolbar.addWidget(self._remove_btn)
        toolbar.addStretch()
        toolbar.addWidget(export_btn)
        outer.addLayout(toolbar)

        self._tabs = QTabWidget()

        self._pending_model = _WatchlistModel()
        self._pending_proxy = QSortFilterProxyModel()
        self._pending_table = _make_table(self._pending_model, self._pending_proxy)
        self._tabs.addTab(self._pending_table, "⏳ Pending")

        self._watched_model = _WatchlistModel()
        self._watched_proxy = QSortFilterProxyModel()
        self._watched_table = _make_table(self._watched_model, self._watched_proxy)
        self._tabs.addTab(self._watched_table, "✓ Watched")

        outer.addWidget(self._tabs, 1)
        self.load_rows()

    def load_rows(self) -> None:
        pending = self._repo.list_items(watched=False)
        watched = self._repo.list_items(watched=True)
        self._pending_model.set_rows(pending)
        self._watched_model.set_rows(watched)
        total = len(pending) + len(watched)
        self._count_lbl.setText(
            f"{len(pending)} pending — {len(watched)} watched — {total} total"
        )
        self._tabs.setTabText(0, f"⏳ Pending ({len(pending)})")
        self._tabs.setTabText(1, f"✓ Watched ({len(watched)})")

    def _current_row(self) -> dict | None:
        tab = self._tabs.currentIndex()
        model = self._pending_model if tab == 0 else self._watched_model
        proxy  = self._pending_proxy  if tab == 0 else self._watched_proxy
        table  = self._pending_table  if tab == 0 else self._watched_table
        sel = table.selectionModel().selectedRows()
        if not sel:
            return None
        src_idx = proxy.mapToSource(sel[0])
        return model.get_row(src_idx.row())

    def _add(self) -> None:
        dlg = _AddDialog(self._repo, parent=self)
        if dlg.exec() == QDialog.Accepted and dlg.entity_id is not None:
            self._repo.add(dlg.entity_id, dlg.priority, dlg.notes)
            self.load_rows()

    def _mark_watched(self) -> None:
        row = self._current_row()
        if row is None:
            QMessageBox.information(self, "No selection", "Select an item first.")
            return
        self._repo.mark_watched(row["id"])
        self.load_rows()

    def _mark_unwatched(self) -> None:
        row = self._current_row()
        if row is None:
            QMessageBox.information(self, "No selection", "Select an item first.")
            return
        self._repo.mark_unwatched(row["id"])
        self.load_rows()

    def _remove(self) -> None:
        row = self._current_row()
        if row is None:
            QMessageBox.information(self, "No selection", "Select an item first.")
            return
        reply = QMessageBox.question(
            self, "Remove from Watchlist",
            f"Remove \u201c{row['title']}\u201d from your watchlist?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._repo.remove(row["id"])
            self.load_rows()

    def _export_csv(self) -> None:
        import csv
        from mlm.app.paths import EXPORT_DIR
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = EXPORT_DIR / f"watchlist_{ts}.csv"
        all_rows = self._repo.list_items()
        if not all_rows:
            QMessageBox.information(self, "Empty", "Your watchlist is empty.")
            return
        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["title", "media_type", "release_year", "rating",
                            "priority", "notes", "added_at", "watched_at"],
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(all_rows)
        QMessageBox.information(self, "Exported", f"Saved to:\n{out}")
