from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

class DuplicatesModel(QAbstractTableModel):
    HEADERS = [
        "Group",
        "Type",
        "Confidence",
        "Filename",
        "Size (GB)",
        "Duration",
        "Resolution",
        "Codec",
        "Path",
    ]

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
            row["group_id"],
            row["match_type"],
            row["confidence"],
            row["file_name"],
            f'{(row["file_size_bytes"] / (1024**3)):.2f}',
            row.get("duration_seconds") or "",
            row.get("resolution") or "",
            row.get("video_codec") or "",
            row["file_path"],
        ]

        if role == Qt.DisplayRole:
            return values[index.column()]

        return None