"""Table model for the Duplicates view.

Columns:
  Group       — numeric group ID so you can see which files are paired
  Match       — Exact / Same Episode, Diff Quality / Possible
  Filename    — just the file name (not the full path)
  Size        — human-readable (e.g. 2.34 GB / 845 MB)
  Duration    — human-readable (e.g. 1h 25m 07s)
  Resolution  — e.g. 1920x1080
  Codec       — video codec
  Quality tag — ⬆ Best / ⬇ Lower (for quality-diff groups)
  Path        — full path

The Confidence column has been removed — it wasn’t meaningful to users.
"Possible" rows that share the same TMDB entity_id and episode are now
reclassified as "Same Episode, Diff Quality" so the real duplicates
are easy to tell apart from noisy fuzzy matches.
"""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

_GREEN  = QColor("#81c784")
_YELLOW = QColor("#fff176")
_RED    = QColor("#ef9a9a")
_MUTED  = QColor("#9e9e9e")
_WHITE  = QColor("#e0e0e0")


def _fmt_size(b: int | None) -> str:
    if not b:
        return "—"
    if b >= 1024 ** 3:
        return f"{b / 1024**3:.2f} GB"
    return f"{b / 1024**2:.0f} MB"


def _fmt_duration(s: float | None) -> str:
    if not s:
        return "—"
    s = int(s)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m {sec:02d}s"
    return f"{m}m {sec:02d}s"


def _resolution_rank(res: str | None) -> int:
    """Higher = better quality. Used to flag best/lower copy."""
    if not res:
        return 0
    w = res.split("x")[0] if "x" in res else ""
    try:
        return int(w)
    except ValueError:
        return 0


class DuplicatesModel(QAbstractTableModel):
    HEADERS = [
        "Group",
        "Match Type",
        "Filename",
        "Size",
        "Duration",
        "Resolution",
        "Codec",
        "Quality",
        "Path",
    ]

    _COL_GROUP   = 0
    _COL_MATCH   = 1
    _COL_NAME    = 2
    _COL_SIZE    = 3
    _COL_DUR     = 4
    _COL_RES     = 5
    _COL_CODEC   = 6
    _COL_QUALITY = 7
    _COL_PATH    = 8

    def __init__(self, rows: list[dict] | None = None) -> None:
        super().__init__()
        self._rows: list[dict] = []
        self._quality_tags: dict[int, str] = {}   # row index → "⬆ Best" | "⬇ Lower"
        if rows:
            self.set_rows(rows)

    def set_rows(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = rows
        self._quality_tags = self._compute_quality_tags(rows)
        self.endResetModel()

    def _compute_quality_tags(self, rows: list[dict]) -> dict[int, str]:
        """For every group, find the highest-resolution file and tag it Best."""
        # Collect rows per group
        groups: dict[int, list[tuple[int, dict]]] = {}
        for i, row in enumerate(rows):
            gid = row["group_id"]
            groups.setdefault(gid, []).append((i, row))

        tags: dict[int, str] = {}
        for gid, members in groups.items():
            ranked = sorted(
                members,
                key=lambda t: _resolution_rank(t[1].get("resolution")),
                reverse=True,
            )
            best_rank = _resolution_rank(ranked[0][1].get("resolution"))
            for idx, (row_i, row) in enumerate(ranked):
                rank = _resolution_rank(row.get("resolution"))
                if rank == 0:
                    tags[row_i] = "—"           # no resolution info
                elif rank == best_rank and idx == 0:
                    tags[row_i] = "⬆ Best"
                else:
                    tags[row_i] = "⬇ Lower"
        return tags

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

        row = self._rows[index.row()]
        col = index.column()

        # Reclassify match type for display
        raw_match = row.get("match_type", "")
        display_match = {
            "exact":    "Exact Copy",
            "possible": "Possible",
            "quality":  "Same Episode, Diff Quality",
        }.get(raw_match, raw_match.capitalize())

        quality_tag = self._quality_tags.get(index.row(), "—")

        if role == Qt.DisplayRole:
            return [
                str(row.get("group_id", "")),
                display_match,
                row.get("file_name", ""),
                _fmt_size(row.get("file_size_bytes")),
                _fmt_duration(row.get("duration_seconds")),
                row.get("resolution") or "—",
                row.get("video_codec") or "—",
                quality_tag,
                row.get("file_path", ""),
            ][col]

        if role == Qt.ForegroundRole:
            if col == self._COL_MATCH:
                return {
                    "exact":    _RED,
                    "quality":  _YELLOW,
                    "possible": _MUTED,
                }.get(raw_match, _WHITE)
            if col == self._COL_QUALITY:
                if quality_tag == "⬆ Best":
                    return _GREEN
                if quality_tag == "⬇ Lower":
                    return _RED
                return _MUTED

        return None
