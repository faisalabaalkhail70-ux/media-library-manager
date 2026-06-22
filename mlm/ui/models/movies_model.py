"""Qt table model for the Movies view."""
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex

COLUMNS = [
    ("title",           "Title"),
    ("release_year",    "Year"),
    ("rating",          "Rating"),
    ("genres",          "Genres"),
    ("resolution",      "Resolution"),
    ("file_size_bytes", "Size (bytes)"),
    ("file_name",       "File Name"),
]


class MoviesTableModel(QAbstractTableModel):
    def __init__(self, rows: list[dict], parent=None) -> None:
        super().__init__(parent)
        self._rows = rows

    def set_rows(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return COLUMNS[section][1]
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        row = self._rows[index.row()]
        key = COLUMNS[index.column()][0]
        value = row.get(key)
        if key == "file_size_bytes" and value is not None:
            return f"{value / (1024**3):.2f} GB" if value > 1024**3 else f"{value / (1024**2):.1f} MB"
        return str(value) if value is not None else ""

    def get_row(self, index: int) -> dict:
        return self._rows[index]
