from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor


class ShowsTableModel(QAbstractTableModel):
    HEADERS = [
        "Title", "Year", "Seasons",
        "Have", "Missing", "Completion %", "Rating", "Genres",
    ]

    def __init__(self, rows: list[dict] | None = None) -> None:
        super().__init__()
        self._rows = rows or []

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

        row  = self._rows[index.row()]
        col  = index.column()
        have = row.get("episodes_have") or 0
        total = row.get("episodes_total") or 0
        missing = row.get("episodes_missing") or 0
        pct  = round(have / total * 100) if total > 0 else 0

        if role == Qt.DisplayRole:
            values = [
                row.get("title", ""),
                str(row.get("release_year", "") or ""),
                str(row.get("seasons_count", "") or ""),
                str(have),
                str(missing),
                f"{pct}%",
                str(row.get("rating", "") or ""),
                row.get("genres", "") or "",
            ]
            return values[col]

        if role == Qt.ForegroundRole and col == 5:
            if pct == 100:
                return QColor("#81c784")
            if pct >= 75:
                return QColor("#fff176")
            return QColor("#ef9a9a")

        if role == Qt.UserRole:
            return row.get("entity_id")

        return None