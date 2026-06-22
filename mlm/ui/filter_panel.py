"""Reusable multi-filter panel for Movies and TV Shows views.

Usage::

    from mlm.ui.filter_panel import FilterPanel
    self._filters = FilterPanel(media_type='movie')   # or 'show'
    self._filters.changed.connect(self._apply_filters)
    layout.addWidget(self._filters)

    # In _apply_filters():
    rows = self._all_rows
    rows = self._filters.apply(rows)
    self._source_model.set_rows(rows)
"""
import json
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox,
    QPushButton, QSlider, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

_RESOLUTIONS = ["Any", "4K", "1080p", "720p", "SD"]
_COMPLETION  = ["Any", "Complete", "Partial", "Not Started"]


def _res_rank(res: str | None) -> str:
    """Normalise a raw resolution string (e.g. '3840x2160') to 4K/1080p/720p/SD."""
    if not res:
        return "SD"
    w = res.split("x")[0] if "x" in res else ""
    try:
        w = int(w)
    except ValueError:
        return "SD"
    if w >= 3840: return "4K"
    if w >= 1920: return "1080p"
    if w >= 1280: return "720p"
    return "SD"


class _LabeledSlider(QWidget):
    """A horizontal slider with a live value label on its right."""
    valueChanged = Signal(int)

    def __init__(self, lo: int, hi: int, step: int = 1, parent=None) -> None:
        super().__init__(parent)
        self._lo, self._hi = lo, hi
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(lo, hi)
        self._slider.setSingleStep(step)
        self._slider.setPageStep(step * 5)
        self._label = QLabel(str(lo))
        self._label.setFixedWidth(38)
        self._label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._slider.valueChanged.connect(lambda v: (self._label.setText(str(v)), self.valueChanged.emit(v)))
        row.addWidget(self._slider)
        row.addWidget(self._label)

    def value(self) -> int: return self._slider.value()
    def setValue(self, v: int) -> None: self._slider.setValue(v)


class FilterPanel(QFrame):
    """Collapsible filter bar — emits `changed` whenever any filter changes."""
    changed = Signal()

    _YEAR_MIN = 1900
    _YEAR_MAX = 2030
    _RATING_MIN = 0
    _RATING_MAX = 10

    def __init__(self, media_type: str = "movie", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("stat_card")
        self._media_type = media_type
        self._visible = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Toggle button row
        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(8, 4, 8, 4)
        self._toggle_btn = QPushButton("▼ Filters")
        self._toggle_btn.setFixedHeight(26)
        self._toggle_btn.clicked.connect(self._toggle)
        self._reset_btn = QPushButton("Reset")
        self._reset_btn.setFixedHeight(26)
        self._reset_btn.clicked.connect(self._reset)
        self._active_lbl = QLabel("")
        self._active_lbl.setObjectName("muted")
        toggle_row.addWidget(self._toggle_btn)
        toggle_row.addWidget(self._active_lbl)
        toggle_row.addStretch()
        toggle_row.addWidget(self._reset_btn)
        outer.addLayout(toggle_row)

        # Filter controls container
        self._panel = QWidget()
        self._panel.setVisible(False)
        panel_layout = QHBoxLayout(self._panel)
        panel_layout.setContentsMargins(8, 6, 8, 8)
        panel_layout.setSpacing(18)

        def _lbl(t): 
            l = QLabel(t)
            l.setObjectName("muted")
            return l

        # Genre
        g1 = QVBoxLayout()
        g1.addWidget(_lbl("Genre"))
        self._genre_cb = QComboBox()
        self._genre_cb.setMinimumWidth(130)
        self._genre_cb.addItem("Any")
        self._genre_cb.currentIndexChanged.connect(self.changed)
        g1.addWidget(self._genre_cb)
        panel_layout.addLayout(g1)

        # Rating range
        g2 = QVBoxLayout()
        g2.addWidget(_lbl("Rating min"))
        self._rating_min = _LabeledSlider(self._RATING_MIN, self._RATING_MAX)
        self._rating_min.valueChanged.connect(lambda _: self.changed.emit())
        g2.addWidget(self._rating_min)
        g2.addWidget(_lbl("Rating max"))
        self._rating_max = _LabeledSlider(self._RATING_MIN, self._RATING_MAX)
        self._rating_max.setValue(self._RATING_MAX)
        self._rating_max.valueChanged.connect(lambda _: self.changed.emit())
        g2.addWidget(self._rating_max)
        panel_layout.addLayout(g2)

        # Year range
        g3 = QVBoxLayout()
        g3.addWidget(_lbl("Year from"))
        self._year_from = _LabeledSlider(self._YEAR_MIN, self._YEAR_MAX, step=1)
        self._year_from.setValue(self._YEAR_MIN)
        self._year_from.valueChanged.connect(lambda _: self.changed.emit())
        g3.addWidget(self._year_from)
        g3.addWidget(_lbl("Year to"))
        self._year_to = _LabeledSlider(self._YEAR_MIN, self._YEAR_MAX, step=1)
        self._year_to.setValue(self._YEAR_MAX)
        self._year_to.valueChanged.connect(lambda _: self.changed.emit())
        g3.addWidget(self._year_to)
        panel_layout.addLayout(g3)

        # Resolution
        g4 = QVBoxLayout()
        g4.addWidget(_lbl("Resolution"))
        self._res_cb = QComboBox()
        self._res_cb.addItems(_RESOLUTIONS)
        self._res_cb.currentIndexChanged.connect(self.changed)
        g4.addWidget(self._res_cb)
        panel_layout.addLayout(g4)

        # Completion status (shows only)
        if media_type == "show":
            g5 = QVBoxLayout()
            g5.addWidget(_lbl("Completion"))
            self._completion_cb = QComboBox()
            self._completion_cb.addItems(_COMPLETION)
            self._completion_cb.currentIndexChanged.connect(self.changed)
            g5.addWidget(self._completion_cb)
            panel_layout.addLayout(g5)
        else:
            self._completion_cb = None

        panel_layout.addStretch()
        outer.addWidget(self._panel)

    # ── Public API ────────────────────────────────────────────────

    def populate_genres(self, rows: list[dict]) -> None:
        """Fill the Genre dropdown from library rows (call after load_rows)."""
        genres: set[str] = set()
        for r in rows:
            for g in r.get("genres", "").split(","):
                g = g.strip()
                if g:
                    genres.add(g)
        current = self._genre_cb.currentText()
        self._genre_cb.blockSignals(True)
        self._genre_cb.clear()
        self._genre_cb.addItem("Any")
        for g in sorted(genres):
            self._genre_cb.addItem(g)
        idx = self._genre_cb.findText(current)
        self._genre_cb.setCurrentIndex(max(idx, 0))
        self._genre_cb.blockSignals(False)

    def apply(self, rows: list[dict]) -> list[dict]:
        """Return a filtered subset of *rows* according to current filter values."""
        genre  = self._genre_cb.currentText()
        r_min  = self._rating_min.value()
        r_max  = self._rating_max.value()
        y_from = self._year_from.value()
        y_to   = self._year_to.value()
        res    = self._res_cb.currentText()
        comp   = self._completion_cb.currentText() if self._completion_cb else "Any"

        active = []
        result = []
        for row in rows:
            # Genre
            if genre != "Any":
                if genre not in row.get("genres", ""):
                    continue

            # Rating
            rating = row.get("rating")
            try:
                rating = float(rating) if rating else 0.0
            except (TypeError, ValueError):
                rating = 0.0
            if not (r_min <= rating <= r_max):
                continue

            # Year
            year = row.get("release_year")
            try:
                year = int(year) if year else self._YEAR_MIN
            except (TypeError, ValueError):
                year = self._YEAR_MIN
            if not (y_from <= year <= y_to):
                continue

            # Resolution
            if res != "Any":
                row_res = _res_rank(row.get("resolution"))
                if row_res != res:
                    continue

            # Completion (shows only)
            if comp != "Any" and self._completion_cb:
                ep_have = row.get("episodes_have") or 0
                ep_miss = row.get("episodes_missing") or 0
                total   = ep_have + ep_miss
                if comp == "Complete"   and not (ep_miss == 0 and ep_have > 0): continue
                if comp == "Not Started" and not (ep_have == 0):                continue
                if comp == "Partial"    and not (ep_have > 0 and ep_miss > 0):  continue

            result.append(row)

        # Update active-filter label
        active_parts = []
        if genre != "Any":             active_parts.append(f"Genre: {genre}")
        if r_min > 0 or r_max < 10:    active_parts.append(f"Rating: {r_min}–{r_max}")
        if y_from > self._YEAR_MIN or y_to < self._YEAR_MAX:
            active_parts.append(f"Year: {y_from}–{y_to}")
        if res != "Any":               active_parts.append(f"Res: {res}")
        if comp != "Any":              active_parts.append(f"Status: {comp}")
        self._active_lbl.setText("  —  " + "  |  ".join(active_parts) if active_parts else "")

        return result

    # ── Private ───────────────────────────────────────────────────

    def _toggle(self) -> None:
        self._visible = not self._visible
        self._panel.setVisible(self._visible)
        self._toggle_btn.setText(("▲ Filters" if self._visible else "▼ Filters"))

    def _reset(self) -> None:
        self._genre_cb.setCurrentIndex(0)
        self._rating_min.setValue(self._RATING_MIN)
        self._rating_max.setValue(self._RATING_MAX)
        self._year_from.setValue(self._YEAR_MIN)
        self._year_to.setValue(self._YEAR_MAX)
        self._res_cb.setCurrentIndex(0)
        if self._completion_cb:
            self._completion_cb.setCurrentIndex(0)
        self.changed.emit()
