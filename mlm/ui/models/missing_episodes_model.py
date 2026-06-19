from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

class MissingEpisodesModel(QAbstractTableModel):
    HEADERS = ["Season", "Episode", "Title", "Air Date", "Status"]

    def __init__(self, rows: list[dict] | None = None) -> None:
        super().__init__()
        self._rows = rows or []

    def set_rows(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

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
            row["season_number"],
            row["episode_number"],
            row.get("episode_title") or "",
            row.get("air_date") or "",
            "Missing" if row.get("is_missing") else "Present",
        ]

        if role == Qt.DisplayRole:
            return values[index.column()]

        if role == Qt.ForegroundRole and row.get("is_missing"):
            return QColor("#ef5350")

        return None