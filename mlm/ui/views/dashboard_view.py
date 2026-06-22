from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QGridLayout, QPushButton, QScrollArea
)
from PySide6.QtCore import Qt
from mlm.services.dashboard_service import DashboardService


def _stat_card(label: str, value: str, accent: str = "#1976d2") -> QFrame:
    card = QFrame()
    card.setObjectName("stat_card")
    card.setFixedHeight(90)
    inner = QVBoxLayout(card)
    inner.setContentsMargins(16, 12, 16, 12)
    val_lbl = QLabel(value)
    val_lbl.setAlignment(Qt.AlignCenter)
    val_lbl.setStyleSheet(f"font-size: 26px; font-weight: 700; color: {accent};")
    lbl = QLabel(label)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet("font-size: 11px; color: #aaaaaa;")
    inner.addWidget(val_lbl)
    inner.addWidget(lbl)
    return card


def _make_donut(complete: int, partial: int, not_started: int) -> QWidget:
    """Build a QtCharts doughnut chart and return it as a QWidget.
    Falls back to a plain text widget if PySide6.QtCharts is unavailable.
    """
    try:
        from PySide6.QtCharts import QChart, QChartView, QPieSeries
        from PySide6.QtGui import QPainter, QColor, QFont

        series = QPieSeries()
        total = complete + partial + not_started

        # Always add all three slices so the legend is stable
        slices_data = [
            ("Complete",    complete,    "#66bb6a"),
            ("Partial",     partial,     "#ffa726"),
            ("Not Started", not_started, "#ef5350"),
        ]
        for label, value, color in slices_data:
            pct = (value / total * 100) if total else 0
            sl = series.append(f"{label}  {value} ({pct:.0f}%)", max(value, 0))
            sl.setColor(QColor(color))
            sl.setLabelColor(QColor("#e0e0e0"))
            sl.setBorderColor(QColor("transparent"))

        series.setHoleSize(0.5)          # makes it a doughnut
        series.setPieSize(0.75)
        series.setLabelsVisible(False)   # labels shown in legend instead

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("TV Show Completion")
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.setBackgroundVisible(False)
        chart.setMargins(__import__('PySide6.QtCore', fromlist=['QMargins']).QMargins(4, 4, 4, 4))
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)

        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        chart.setTitleFont(title_font)
        chart.setTitleBrush(__import__('PySide6.QtGui', fromlist=['QBrush']).QBrush(QColor("#e0e0e0")))

        for lbl in chart.legend().markers(series):
            lbl.setLabelBrush(__import__('PySide6.QtGui', fromlist=['QBrush']).QBrush(QColor("#cccccc")))

        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setMinimumHeight(280)
        view.setStyleSheet("background: transparent;")
        return view

    except ImportError:
        # QtCharts not installed — render a compact text fallback
        frame = QFrame()
        frame.setObjectName("stat_card")
        lay = QVBoxLayout(frame)
        title = QLabel("TV Show Completion")
        title.setStyleSheet("font-weight: 700; font-size: 14px;")
        lay.addWidget(title)
        total = complete + partial + not_started or 1
        for label, value, color in [
            ("Complete",    complete,    "#66bb6a"),
            ("Partial",     partial,     "#ffa726"),
            ("Not Started", not_started, "#ef5350"),
        ]:
            pct = value / total * 100
            row = QLabel(f"<span style='color:{color}'>●</span>  {label}: {value} ({pct:.0f}%)")
            row.setTextFormat(Qt.RichText)
            lay.addWidget(row)
        lay.addStretch()
        return frame


class DashboardView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.service = DashboardService()
        self._donut_widget = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(24, 20, 24, 20)
        self._layout.setSpacing(20)

        # ── Header ──────────────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("h1")
        header.addWidget(title)
        header.addStretch()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_rows)
        header.addWidget(self.refresh_btn)
        self._layout.addLayout(header)

        # ── Stats grid ─────────────────────────────────────────────────
        self.grid = QGridLayout()
        self.grid.setSpacing(12)
        self._layout.addLayout(self.grid)

        # ── Bottom row: chart + breakdowns ──────────────────────────────
        self._bottom_row = QHBoxLayout()
        self._bottom_row.setSpacing(16)
        self._layout.addLayout(self._bottom_row)

        # Donut placeholder
        self._donut_slot = QVBoxLayout()
        self._bottom_row.addLayout(self._donut_slot, 2)

        # Resolution + Codec cards stacked on the right
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        res_box = QFrame()
        res_box.setObjectName("stat_card")
        res_inner = QVBoxLayout(res_box)
        res_lbl = QLabel("Resolution Breakdown")
        res_lbl.setStyleSheet("font-weight: 700;")
        res_inner.addWidget(res_lbl)
        self.res_content = QLabel("—")
        self.res_content.setObjectName("muted")
        self.res_content.setWordWrap(True)
        res_inner.addWidget(self.res_content)
        right_col.addWidget(res_box)

        codec_box = QFrame()
        codec_box.setObjectName("stat_card")
        codec_inner = QVBoxLayout(codec_box)
        codec_lbl = QLabel("Codec Breakdown")
        codec_lbl.setStyleSheet("font-weight: 700;")
        codec_inner.addWidget(codec_lbl)
        self.codec_content = QLabel("—")
        self.codec_content.setObjectName("muted")
        self.codec_content.setWordWrap(True)
        codec_inner.addWidget(self.codec_content)
        right_col.addWidget(codec_box)

        self._bottom_row.addLayout(right_col, 1)

        # ── Recent additions ─────────────────────────────────────────
        recent_lbl = QLabel("Recently Added")
        recent_lbl.setStyleSheet("font-size: 15px; font-weight: 700;")
        self._layout.addWidget(recent_lbl)

        self.recent_container = QVBoxLayout()
        self.recent_container.setSpacing(4)
        recent_wrap = QWidget()
        recent_wrap.setLayout(self.recent_container)
        self._layout.addWidget(recent_wrap)

        self._layout.addStretch()
        self.load_rows()

    def load_rows(self) -> None:
        overview   = self.service.library_overview()
        missing_ep = self.service.missing_episodes_count()
        completion = self.service.shows_completion()

        # ── Stat cards ───────────────────────────────────────────────
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        stats = [
            ("Movies",           str(overview["total_movies"]),   "#42a5f5"),
            ("TV Shows",         str(overview["total_shows"]),    "#66bb6a"),
            ("Episodes",         str(overview["total_episodes"]), "#ab47bc"),
            ("Unmatched Files",  str(overview["unmatched"]),      "#ef5350"),
            ("Missing Episodes", str(missing_ep),                 "#ffa726"),
            ("Storage (GB)",     str(overview["storage_gb"]),     "#26c6da"),
            ("Watch Hours",      str(overview["watch_hours"]),    "#8d6e63"),
            ("Total Files",      str(overview["total_files"]),    "#78909c"),
        ]
        for i, (label, value, accent) in enumerate(stats):
            self.grid.addWidget(_stat_card(label, value, accent), i // 4, i % 4)

        # ── Donut chart (rebuild in place) ─────────────────────────────
        if self._donut_widget is not None:
            self._donut_slot.removeWidget(self._donut_widget)
            self._donut_widget.deleteLater()

        self._donut_widget = _make_donut(
            completion["complete"],
            completion["partial"],
            completion["not_started"],
        )
        self._donut_slot.addWidget(self._donut_widget)

        # ── Resolution / Codec breakdowns ────────────────────────────
        res_rows = self.service.resolution_breakdown()
        self.res_content.setText(
            "\n".join(f'{r["resolution"]}: {r["count"]}' for r in res_rows[:8]) or "No data"
        )
        codec_rows = self.service.codec_breakdown()
        self.codec_content.setText(
            "\n".join(f'{r["video_codec"]}: {r["count"]}' for r in codec_rows[:8]) or "No data"
        )

        # ── Recent additions ─────────────────────────────────────────
        while self.recent_container.count():
            item = self.recent_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for row in self.service.recent_additions(limit=10):
            lbl = QLabel(
                f'• {row["file_name"]}'
                f'  <span style="color:#888">{str(row["discovered_at"])[:10]}</span>'
            )
            lbl.setObjectName("muted")
            lbl.setTextFormat(Qt.RichText)
            self.recent_container.addWidget(lbl)
