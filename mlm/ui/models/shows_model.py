"""Qt table model for the TV Shows view — semantic color coding on every column."""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

_GREEN   = QColor("#81c784")
_YELLOW  = QColor("#fff176")
_AMBER   = QColor("#ffa726")
_RED     = QColor("#ef9a9a")
_MUTED   = QColor("#6e6e8a")
_NORMAL  = QColor("#d0d0e8")

_CENTER = Qt.AlignHCenter | Qt.AlignVCenter
_LEFT   = Qt.AlignLeft    | Qt.AlignVCenter


def _rating_color(rating) -> QColor:
    try:
        r = float(rating)
    except (TypeError, ValueError):
        return _MUTED
    if r >= 7.0: return _GREEN
    if r >= 5.0: return _YELLOW
    return _RED


class ShowsTableModel(QAbstractTableModel):
    HEADERS = [
        "Title",
        "Year",
        "Seasons Have",
        "Seasons Missing",
        "Episodes Have",
        "Episodes Missing",
        "Completion %",
        "Rating",
        "Genres",
    ]

    _COL_TITLE  = 0
    _COL_YEAR   = 1
    _COL_S_HAVE = 2
    _COL_S_MISS = 3
    _COL_E_HAVE = 4
    _COL_E_MISS = 5
    _COL_PCT    = 6
    _COL_RATING = 7
    _COL_GENRES = 8

    # Columns that should be horizontally centered
    _CENTERED_COLS = {_COL_YEAR, _COL_S_HAVE, _COL_S_MISS,
                      _COL_E_HAVE, _COL_E_MISS, _COL_PCT, _COL_RATING}

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

        ep_have  = row.get("episodes_have")    or 0
        ep_miss  = row.get("episodes_missing") or 0
        s_have   = row.get("seasons_have")     or 0
        s_miss   = row.get("seasons_missing")  or 0
        ep_total = ep_have + ep_miss
        pct      = round(ep_have / ep_total * 100) if ep_total > 0 else 0

        # ── Rating: round to 1 decimal place ────────────────────────────────────────
        raw_rating = row.get("rating")
        try:
            rating_display = f"{float(raw_rating):.1f}"
        except (TypeError, ValueError):
            rating_display = ""

        if role == Qt.DisplayRole:
            return [
                row.get("title", ""),
                str(row.get("release_year", "") or ""),
                str(s_have)  if s_have  else "—",
                str(s_miss)  if s_miss  else "—",
                str(ep_have) if ep_have else "—",
                str(ep_miss) if ep_miss else "—",
                f"{pct}%",
                rating_display,
                row.get("genres", "") or "",
            ][col]

        if role == Qt.TextAlignmentRole:
            return int(_CENTER if col in self._CENTERED_COLS else _LEFT)

        if role == Qt.ForegroundRole:
            # ── Always return an explicit color — never None — so Qt's
            # alternating-row palette never overrides our choices.
            if col == self._COL_TITLE:
                return _NORMAL
            if col == self._COL_YEAR:
                return _MUTED
            if col == self._COL_S_HAVE:
                return _GREEN if s_have > 0 else _MUTED
            if col == self._COL_S_MISS:
                return _RED   if s_miss > 0 else _MUTED
            if col == self._COL_E_HAVE:
                return _GREEN if ep_have > 0 else _MUTED
            if col == self._COL_E_MISS:
                return _RED   if ep_miss > 0 else _MUTED
            if col == self._COL_PCT:
                if pct == 100:  return _GREEN
                if pct >= 75:   return _YELLOW
                if pct >= 40:   return _AMBER
                return _RED
            if col == self._COL_RATING:
                return _rating_color(raw_rating)
            if col == self._COL_GENRES:
                return _MUTED
            return _NORMAL

        if role == Qt.UserRole:
            return row.get("entity_id")

        return None
