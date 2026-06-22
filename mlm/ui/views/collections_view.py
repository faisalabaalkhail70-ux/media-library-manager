"""Collections sidebar view.

Layout
-------
Left column (240 px) — list of collections with New / Rename / Delete toolbar.
Right column         — table of items in the selected collection,
                         with Add Item / Remove Item toolbar.

All DB work goes through CollectionsRepository so this view is pure UI.
"""
import json

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTableView, QAbstractItemView,
    QFrame, QInputDialog, QMessageBox, QDialog, QLineEdit,
    QDialogButtonBox, QSplitter
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QColor

from mlm.db.repositories.collections_repo import CollectionsRepository


# ── Lightweight table model for collection items ──────────────────────────
class _ItemsModel(QAbstractTableModel):
    HEADERS = ["Title", "Type", "Year", "Rating", "Genres"]

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
        if role == Qt.DisplayRole:
            if col == 0: return row.get("title", "")
            if col == 1: return row.get("media_type", "").capitalize()
            if col == 2: return str(row.get("release_year") or "")
            if col == 3: return str(row.get("rating") or "")
            if col == 4:
                try:
                    genres = json.loads(row.get("genres_json") or "[]")
                    return ", ".join(g.get("name", "") for g in genres)
                except Exception:
                    return ""
        if role == Qt.ForegroundRole:
            mt = row.get("media_type", "")
            if mt == "movie": return QColor("#42a5f5")
            if mt == "show":  return QColor("#66bb6a")
        if role == Qt.UserRole:
            return row.get("entity_id")
        return None


# ── Add-item search dialog ────────────────────────────────────────────────
class _AddItemDialog(QDialog):
    """Search media_entities and pick one to add to the collection."""

    def __init__(self, repo: CollectionsRepository, collection_id: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Item to Collection")
        self.setMinimumWidth(480)
        self._repo = repo
        self._collection_id = collection_id
        self._selected_entity_id: int | None = None

        lay = QVBoxLayout(self)
        lay.setSpacing(8)

        lay.addWidget(QLabel("Search for a movie or show:"))
        self._search = QLineEdit()
        self._search.setPlaceholderText("Type to search...")
        self._search.textChanged.connect(self._do_search)
        lay.addWidget(self._search)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._on_double_click)
        lay.addWidget(self._list)

        self._status = QLabel("")
        self._status.setObjectName("muted")
        lay.addWidget(self._status)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

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

    def _on_double_click(self, item: QListWidgetItem) -> None:
        self._selected_entity_id = item.data(Qt.UserRole)
        self.accept()

    def _on_accept(self) -> None:
        sel = self._list.currentItem()
        if sel:
            self._selected_entity_id = sel.data(Qt.UserRole)
        self.accept()

    @property
    def entity_id(self) -> int | None:
        return self._selected_entity_id


# ── Main view ────────────────────────────────────────────────────────────
class CollectionsView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._repo = CollectionsRepository()
        self._current_collection_id: int | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("Collections")
        title.setObjectName("h1")
        hdr.addWidget(title)
        hdr.addStretch()
        outer.addLayout(hdr)

        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        outer.addWidget(splitter, 1)

        # ── Left panel: collection list ───────────────────────────
        left = QWidget()
        left.setMinimumWidth(200)
        left.setMaximumWidth(300)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(6)

        col_toolbar = QHBoxLayout()
        new_btn = QPushButton("+ New")
        new_btn.setFixedHeight(28)
        new_btn.clicked.connect(self._new_collection)
        rename_btn = QPushButton("Rename")
        rename_btn.setFixedHeight(28)
        rename_btn.clicked.connect(self._rename_collection)
        delete_btn = QPushButton("Delete")
        delete_btn.setFixedHeight(28)
        delete_btn.setObjectName("danger")
        delete_btn.clicked.connect(self._delete_collection)
        col_toolbar.addWidget(new_btn)
        col_toolbar.addWidget(rename_btn)
        col_toolbar.addWidget(delete_btn)
        left_lay.addLayout(col_toolbar)

        self._col_list = QListWidget()
        self._col_list.currentItemChanged.connect(self._on_collection_selected)
        left_lay.addWidget(self._col_list)
        splitter.addWidget(left)

        # ── Right panel: items table ──────────────────────────────
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(6)

        item_toolbar = QHBoxLayout()
        self._col_name_lbl = QLabel("Select a collection")
        self._col_name_lbl.setStyleSheet("font-weight: 700; font-size: 14px;")
        add_item_btn = QPushButton("+ Add Item")
        add_item_btn.setFixedHeight(28)
        add_item_btn.clicked.connect(self._add_item)
        remove_item_btn = QPushButton("Remove Item")
        remove_item_btn.setFixedHeight(28)
        remove_item_btn.clicked.connect(self._remove_item)
        self._items_count_lbl = QLabel("")
        self._items_count_lbl.setObjectName("muted")
        item_toolbar.addWidget(self._col_name_lbl)
        item_toolbar.addStretch()
        item_toolbar.addWidget(self._items_count_lbl)
        item_toolbar.addWidget(add_item_btn)
        item_toolbar.addWidget(remove_item_btn)
        right_lay.addLayout(item_toolbar)

        self._items_model = _ItemsModel()
        self._items_proxy = QSortFilterProxyModel()
        self._items_proxy.setSourceModel(self._items_model)
        self._items_proxy.setSortCaseSensitivity(Qt.CaseInsensitive)

        self._items_table = QTableView()
        self._items_table.setModel(self._items_proxy)
        self._items_table.horizontalHeader().setStretchLastSection(True)
        self._items_table.setAlternatingRowColors(True)
        self._items_table.verticalHeader().setVisible(False)
        self._items_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._items_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._items_table.setSortingEnabled(True)
        right_lay.addWidget(self._items_table)
        splitter.addWidget(right)

        splitter.setSizes([240, 700])
        self.load_rows()

    # ── Data loading ──────────────────────────────────────────────

    def load_rows(self) -> None:
        """Reload the collection list (called by MainWindow on navigation)."""
        prev_id = self._current_collection_id
        self._col_list.clear()
        for col in self._repo.list_collections():
            item = QListWidgetItem(f"{col['name']}  ({col['item_count']})") 
            item.setData(Qt.UserRole, col["id"])
            self._col_list.addItem(item)
            if col["id"] == prev_id:
                self._col_list.setCurrentItem(item)
        if self._col_list.currentItem() is None and self._col_list.count() > 0:
            self._col_list.setCurrentRow(0)

    def _load_items(self, collection_id: int) -> None:
        rows = self._repo.get_items(collection_id)
        self._items_model.set_rows(rows)
        self._items_count_lbl.setText(f"{len(rows)} item(s)")

    # ── Collection actions ────────────────────────────────────────

    def _on_collection_selected(self, current: QListWidgetItem, _) -> None:
        if current is None:
            self._current_collection_id = None
            self._col_name_lbl.setText("Select a collection")
            self._items_model.set_rows([])
            self._items_count_lbl.setText("")
            return
        cid = current.data(Qt.UserRole)
        self._current_collection_id = cid
        # Extract name without item count
        self._col_name_lbl.setText(current.text().rsplit("  (", 1)[0])
        self._load_items(cid)

    def _new_collection(self) -> None:
        name, ok = QInputDialog.getText(self, "New Collection", "Collection name:")
        if ok and name.strip():
            try:
                self._repo.create_collection(name)
                self.load_rows()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _rename_collection(self) -> None:
        if self._current_collection_id is None:
            QMessageBox.information(self, "No selection", "Select a collection first.")
            return
        current_name = self._col_name_lbl.text()
        name, ok = QInputDialog.getText(self, "Rename Collection", "New name:", text=current_name)
        if ok and name.strip():
            try:
                self._repo.rename_collection(self._current_collection_id, name)
                self.load_rows()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _delete_collection(self) -> None:
        if self._current_collection_id is None:
            QMessageBox.information(self, "No selection", "Select a collection first.")
            return
        name = self._col_name_lbl.text()
        reply = QMessageBox.question(
            self, "Delete Collection",
            f"Delete \u201c{name}\u201d and all its items? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._repo.delete_collection(self._current_collection_id)
            self._current_collection_id = None
            self.load_rows()

    # ── Item actions ──────────────────────────────────────────────

    def _add_item(self) -> None:
        if self._current_collection_id is None:
            QMessageBox.information(self, "No collection", "Select or create a collection first.")
            return
        dlg = _AddItemDialog(self._repo, self._current_collection_id, parent=self)
        if dlg.exec() == QDialog.Accepted and dlg.entity_id is not None:
            self._repo.add_item(self._current_collection_id, dlg.entity_id)
            self._load_items(self._current_collection_id)
            self.load_rows()  # refresh count in sidebar

    def _remove_item(self) -> None:
        if self._current_collection_id is None:
            return
        sel = self._items_table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "No selection", "Select an item to remove.")
            return
        source_idx = self._items_proxy.mapToSource(sel[0])
        row = self._items_model.get_row(source_idx.row())
        entity_id = row.get("entity_id")
        self._repo.remove_item(self._current_collection_id, entity_id)
        self._load_items(self._current_collection_id)
        self.load_rows()
