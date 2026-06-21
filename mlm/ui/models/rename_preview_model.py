from PySide6.QtCore import Qt, QModelIndex, QAbstractTableModel
from PySide6.QtGui import QColor


class RenamePreviewModel(QAbstractTableModel):
    HEADERS = ["ID", "Current Name", "Proposed Name", "Status", "Current Path", "New Path"]

    def __init__(self, rows: list[dict] | None = None) -> None:
        super().__init__()
        self._rows = rows or []

    def set_rows(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()

    def rows(self) -> list[dict]:
        return self._rows

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal and 0 <= section < len(self.HEADERS):
            return self.HEADERS[section]

        if orientation == Qt.Vertical:
            return str(section + 1)

        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row = self._rows[index.row()]
        values = [
            row.get("media_file_id", ""),
            row.get("old_name", ""),
            row.get("new_name", ""),
            row.get("status", ""),
            row.get("old_path", ""),
            row.get("new_path", ""),
        ]

        if role == Qt.DisplayRole:
            value = values[index.column()]
            return "" if value is None else str(value)

        if role == Qt.ForegroundRole:
            status = str(row.get("status", "")).lower()
            if status == "valid":
                return QColor("#81c784")
            if status == "conflict":
                return QColor("#ffb74d")
            if status == "invalid":
                return QColor("#ef5350")
            if status == "unchanged":
                return QColor("#b0bec5")

        if role == Qt.TextAlignmentRole and index.column() in (0, 3):
            return Qt.AlignCenter

        return None