"""Qt table model for the Library / all-files view — with semantic color coding."""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

_GREEN   = QColor("#81c784")
_YELLOW  = QColor("#fff176")
_AMBER   = QColor("#ffa726")
_RED     = QColor("#ef9a9a")
_CYAN    = QColor("#4dd0e1")
_MUTED   = QColor("#6e6e8a")
_NORMAL  = QColor("#d0d0e8")
_UNMATCHED = QColor("#ef5350")  # brighter red for Unmatched label


def _fmt_size(size_bytes: int | None) -> str:
    if not size_bytes:
        return ""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024 ** 2:.0f} MB"
    return f"{size_bytes / 1024 ** 3:.2f} GB"


def _res_color(res: str | None) -> QColor:
    if not res:
        return _MUTED
    w = res.split("x")[0] if "x" in res else res.lower().replace("p", "")
    try:
        w = int(w)
    except ValueError:
        return _MUTED
    if w >= 3840: return _CYAN
    if w >= 1920: return _GREEN
    if w >= 1280: return _YELLOW
    return _AMBER


def _size_color(size_bytes: int | None) -> QColor:
    if not size_bytes:
        return _MUTED
    gb = size_bytes / (1024 ** 3)
    if gb >= 20: return _CYAN
    if gb >= 4:  return _GREEN
    if gb >= 1:  return _YELLOW
    return _MUTED


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

    _SORT_KEYS = [
        "id",
        "file_name",
        "matched_title",
        "release_year",
        "resolution",
        "video_codec",
        "file_size_bytes",
        "duration_seconds",
        "modified_at",
        "file_path",
    ]

    _COL_ID       = 0
    _COL_FILENAME = 1
    _COL_TITLE    = 2
    _COL_YEAR     = 3
    _COL_RES      = 4
    _COL_CODEC    = 5
    _COL_SIZE     = 6
    _COL_DUR      = 7
    _COL_MOD      = 8
    _COL_PATH     = 9

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

        if role == Qt.ForegroundRole:
            # Matched Title: bright red for Unmatched
            if col == self._COL_TITLE:
                matched = row.get("matched_title", "")
                return _UNMATCHED if not matched else _GREEN
            # Resolution: quality gradient
            if col == self._COL_RES:
                return _res_color(row.get("resolution"))
            # File size: scale by GB
            if col == self._COL_SIZE:
                return _size_color(row.get("file_size_bytes"))
            # Codec: highlight common codecs
            if col == self._COL_CODEC:
                codec = (row.get("video_codec") or "").lower()
                if codec in ("hevc", "h265", "av1"):   return _CYAN    # modern
                if codec in ("h264", "avc"):            return _GREEN   # good
                if codec in ("mpeg2", "mpeg4", "xvid"): return _AMBER   # legacy
                return _MUTED
            # Path and filename: muted
            if col in (self._COL_PATH, self._COL_FILENAME):
                return _MUTED
            return _NORMAL

        if role == Qt.UserRole:
            key = self._SORT_KEYS[col] if col < len(self._SORT_KEYS) else None
            return row.get(key) if key else None

        if role == Qt.TextAlignmentRole:
            if col in {self._COL_ID, self._COL_YEAR, self._COL_SIZE}:
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
