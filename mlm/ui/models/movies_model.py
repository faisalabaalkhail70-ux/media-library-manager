"""Qt table model for the Movies view — with semantic color coding."""
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor

# Shared palette
_GREEN   = QColor("#81c784")
_YELLOW  = QColor("#fff176")
_AMBER   = QColor("#ffa726")
_RED     = QColor("#ef9a9a")
_CYAN    = QColor("#4dd0e1")
_BLUE    = QColor("#64b5f6")
_MUTED   = QColor("#6e6e8a")
_NORMAL  = QColor("#d0d0e8")

COLUMNS = [
    ("title",           "Title"),
    ("release_year",    "Year"),
    ("rating",          "Rating"),
    ("genres",          "Genres"),
    ("resolution",      "Resolution"),
    ("file_size_bytes", "Size"),
    ("file_name",       "File Name"),
]

_COL_TITLE  = 0
_COL_YEAR   = 1
_COL_RATING = 2
_COL_GENRES = 3
_COL_RES    = 4
_COL_SIZE   = 5
_COL_FILE   = 6


def _res_color(res: str | None) -> QColor:
    """Color-code by resolution quality."""
    if not res:
        return _MUTED
    w = res.split("x")[0] if "x" in res else res.lower().replace("p", "")
    try:
        w = int(w)
    except ValueError:
        return _MUTED
    if w >= 3840: return _CYAN    # 4K+  → cyan
    if w >= 1920: return _GREEN   # 1080p → green
    if w >= 1280: return _YELLOW  # 720p  → yellow
    return _AMBER                  # SD    → amber


def _rating_color(rating) -> QColor:
    """Green ≥ 7, yellow ≥ 5, red < 5, muted if absent."""
    try:
        r = float(rating)
    except (TypeError, ValueError):
        return _MUTED
    if r >= 7.0: return _GREEN
    if r >= 5.0: return _YELLOW
    return _RED


def _size_color(size_bytes: int | None) -> QColor:
    """Cyan > 20 GB, green > 4 GB, yellow > 1 GB, muted otherwise."""
    if not size_bytes:
        return _MUTED
    gb = size_bytes / (1024 ** 3)
    if gb >= 20: return _CYAN
    if gb >= 4:  return _GREEN
    if gb >= 1:  return _YELLOW
    return _MUTED


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
        if not index.isValid():
            return None

        row = self._rows[index.row()]
        col = index.column()
        key = COLUMNS[col][0]
        value = row.get(key)

        if role == Qt.DisplayRole:
            if key == "file_size_bytes" and value is not None:
                return (
                    f"{value / (1024**3):.2f} GB"
                    if value > 1024 ** 3
                    else f"{value / (1024**2):.1f} MB"
                )
            return str(value) if value is not None else ""

        if role == Qt.ForegroundRole:
            if col == _COL_RATING:
                return _rating_color(value)
            if col == _COL_RES:
                return _res_color(value)
            if col == _COL_SIZE:
                return _size_color(row.get("file_size_bytes"))
            if col == _COL_FILE:
                return _MUTED
            return _NORMAL

        return None

    def get_row(self, index: int) -> dict:
        return self._rows[index]
