from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

class RenamePreviewModel(QAbstractTableModel):
    HEADERS = ["ID", "Current Name", "Proposed Name", "Status", "Current Path"]

    def __init__(self, rows: list[dict] | None = None) -> None:
        super().__init__()
        self._rows = rows or []

    def set_rows(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rows(self) -> list[dict]:
        return self._rows

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
        values = [
            row["media_file_id"],
            row["old_name"],
            row["new_name"],
            row["status"],
            row["old_path"],
        ]

        if role == Qt.DisplayRole:
            return values[index.column()]

        if role == Qt.ForegroundRole:
            status = row["status"]
            if status == "valid":
                return QColor("#81c784")
            if status == "conflict":
                return QColor("#ffb74d")
            if status == "invalid":
                return QColor("#ef5350")

        return None