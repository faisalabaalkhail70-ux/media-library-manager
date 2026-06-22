"""Model for the missing/present episodes list inside ShowDetailView."""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

_GREEN = QColor("#81c784")
_RED   = QColor("#ef9a9a")
_MUTED = QColor("#6e6e8a")


class MissingEpisodesModel(QAbstractTableModel):
    HEADERS = ["Season", "Episode", "Title", "Air Date", "Status"]

    _COL_SEASON  = 0
    _COL_EPISODE = 1
    _COL_TITLE   = 2
    _COL_AIRDATE = 3
    _COL_STATUS  = 4

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
        col = index.column()
        is_missing = bool(row.get("is_missing"))

        values = [
            row["season_number"],
            row["episode_number"],
            row.get("episode_title") or "",
            row.get("air_date") or "",
            "Missing" if is_missing else "Present",
        ]

        if role == Qt.DisplayRole:
            return values[col]

        if role == Qt.ForegroundRole:
            # Status column: green = present, red = missing
            if col == self._COL_STATUS:
                return _RED if is_missing else _GREEN
            # Metadata columns: muted for missing, normal for present
            return _MUTED if is_missing else QColor("#d0d0e8")

        return None
