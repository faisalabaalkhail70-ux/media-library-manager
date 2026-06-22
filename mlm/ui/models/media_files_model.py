from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt


def _fmt_size(size_bytes: int | None) -> str:
    """Human-readable size: bytes → KB / MB / GB."""
    if not size_bytes:
        return ""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024 ** 2:.0f} MB"
    return f"{size_bytes / 1024 ** 3:.2f} GB"


class MediaFilesTableModel(QAbstractTableModel):
    HEADERS = [
        "ID",
        "Filename",
        "Matched Title",
        "Year",
        "Resolution",
        "Codec",
        "Size",
        "Duration",
        "Modified",
        "Path",
    ]

    # Map column index → row key for sorting
    _SORT_KEYS = [
        "id",
        "file_name",
        "matched_title",
        "release_year",
        "resolution",
        "video_codec",
        "file_size_bytes",   # sort numerically even though display is formatted
        "duration_seconds",
        "modified_at",
        "file_path",
    ]

    def __init__(self, rows: list[dict] | None = None) -> None:
        super().__init__()
        self._rows: list[dict] = rows or []
        self._sort_col = -1
        self._sort_asc = True

    def set_rows(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()
        if self._sort_col >= 0:
            self.sort(self._sort_col, Qt.AscendingOrder if self._sort_asc else Qt.DescendingOrder)

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
            dur = row.get("duration_seconds")
            if dur:
                m, s = divmod(int(dur), 60)
                h, m = divmod(m, 60)
                dur_str = f"{h}h {m:02d}m" if h else f"{m}m {s:02d}s"
            else:
                dur_str = ""
            values = [
                row.get("id"),
                row.get("file_name", ""),
                row.get("matched_title", "") or "Unmatched",
                row.get("release_year", "") or "",
                row.get("resolution", "") or "",
                row.get("video_codec", "") or "",
                _fmt_size(row.get("file_size_bytes")),
                dur_str,
                row.get("modified_at", "") or "",
                row.get("file_path", ""),
            ]
            return values[col]

        if role == Qt.UserRole:
            # Raw value used for sorting
            key = self._SORT_KEYS[col] if col < len(self._SORT_KEYS) else None
            return row.get(key) if key else None

        if role == Qt.TextAlignmentRole:
            if col in {0, 3, 6}:
                return int(Qt.AlignRight | Qt.AlignVCenter)

        return None

    def sort(self, column: int, order=Qt.AscendingOrder) -> None:
        if column < 0 or column >= len(self._SORT_KEYS):
            return
        self._sort_col = column
        self._sort_asc = order == Qt.AscendingOrder
        key = self._SORT_KEYS[column]
        self.beginResetModel()
        self._rows.sort(
            key=lambda r: (r.get(key) is None, r.get(key) or ""),
            reverse=not self._sort_asc,
        )
        self.endResetModel()

    def get_row(self, row_index: int) -> dict:
        return self._rows[row_index]
