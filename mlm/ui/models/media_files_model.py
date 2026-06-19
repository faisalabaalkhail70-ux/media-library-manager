from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

class MediaFilesTableModel(QAbstractTableModel):
    HEADERS = [
        "ID",
        "Filename",
        "Matched Title",
        "Year",
        "Resolution",
        "Codec",
        "Size (GB)",
        "Modified",
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
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return str(section + 1)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row = self._rows[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            values = [
                row.get("id"),
                row.get("file_name", ""),
                row.get("matched_title", "") or "Unmatched",
                row.get("release_year", "") or "",
                row.get("resolution", "") or "",
                row.get("video_codec", "") or "",
                f'{(row.get("file_size_bytes", 0) / (1024**3)):.2f}',
                row.get("modified_at", "") or "",
                row.get("file_path", ""),
            ]
            return values[col]

        if role == Qt.TextAlignmentRole:
            if col in {0, 3, 6}:
                return int(Qt.AlignRight | Qt.AlignVCenter)

        return None