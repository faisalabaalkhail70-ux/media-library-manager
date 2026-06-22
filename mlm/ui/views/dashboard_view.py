"""Dashboard — redesigned with NeonStatCards, GlassCards, SectionHeaders."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QGridLayout, QPushButton, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from mlm.services.dashboard_service import DashboardService
from mlm.ui.widgets import NeonStatCard, GlassCard, SectionHeader, AmbientBackground


# Per-stat accent palette
_ACCENTS = [
    QColor(66, 165, 245),    # Movies        → blue
    QColor(102, 187, 106),   # TV Shows       → green
    QColor(171,  71, 188),   # Episodes       → purple
    QColor(239,  83,  80),   # Unmatched      → red
    QColor(255, 167,  38),   # Missing Ep     → amber
    QColor( 38, 198, 218),   # Storage        → cyan
    QColor(141, 110,  99),   # Watch Hours    → brown
    QColor(120, 144, 156),   # Total Files    → grey-blue
]


def _make_donut(complete: int, partial: int, not_started: int) -> QWidget:
    try:
        from PySide6.QtCharts import QChart, QChartView, QPieSeries
        from PySide6.QtGui import QPainter, QColor, QFont, QBrush
        from PySide6.QtCore import QMargins

        series = QPieSeries()
        total = complete + partial + not_started
        for label, value, color in [
            ("Complete",    complete,    "#66bb6a"),
            ("Partial",     partial,     "#ffa726"),
            ("Not Started", not_started, "#ef5350"),
        ]:
            pct = (value / total * 100) if total else 0
            sl = series.append(f"{label}  {value} ({pct:.0f}%)", max(value, 0))
            sl.setColor(QColor(color))
            sl.setLabelColor(QColor("#e0e0e0"))
            sl.setBorderColor(QColor("transparent"))

        series.setHoleSize(0.52)
        series.setPieSize(0.78)
        series.setLabelsVisible(False)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Show Completion")
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.setBackgroundVisible(False)
        chart.setMargins(QMargins(0, 0, 0, 0))
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)

        tf = QFont("Segoe UI", 12, QFont.Bold)
        chart.setTitleFont(tf)
        chart.setTitleBrush(QBrush(QColor(200, 200, 230)))
        for m in chart.legend().markers(series):
            m.setLabelBrush(QBrush(QColor(160, 160, 190)))

        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setMinimumHeight(260)
        view.setStyleSheet("background: transparent;")
        return view
    except ImportError:
        frame = QFrame()
        frame.setObjectName("stat_card")
        lay = QVBoxLayout(frame)
        total = complete + partial + not_started or 1
        for label, value, color in [
            ("Complete", complete, "#66bb6a"),
            ("Partial",  partial,  "#ffa726"),
            ("Not Started", not_started, "#ef5350"),
        ]:
            pct = value / total * 100
            lbl = QLabel(f"<span style='color:{color}'>●</span>  {label}: {value} ({pct:.0f}%)")
            lbl.setTextFormat(Qt.RichText)
            lay.addWidget(lbl)
        lay.addStretch()
        return frame


class DashboardView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.service = DashboardService()
        self._donut_widget = None
        self._stat_cards: list[NeonStatCard] = []

        # Ambient background (behind everything)
        self._bg = AmbientBackground(self)
        self._bg.lower()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        outer.addWidget(scroll)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        scroll.setWidget(container)
        self._root = QVBoxLayout(container)
        self._root.setContentsMargins(28, 24, 28, 28)
        self._root.setSpacing(24)

        # ── Header row
        hdr = QHBoxLayout()
        from mlm.ui.widgets import GradientLabel
        title = GradientLabel(
            "Dashboard",
            QColor(200, 195, 255),
            QColor(124, 111, 255),
            font_size=22,
        )
        title.setFixedHeight(36)
        hdr.addWidget(title)
        hdr.addStretch()
        refresh_btn = QPushButton("  ↻  Refresh")
        refresh_btn.setObjectName("primary")
        refresh_btn.setFixedHeight(34)
        refresh_btn.clicked.connect(self.load_rows)
        hdr.addWidget(refresh_btn)
        self._root.addLayout(hdr)

        # ── Stat cards grid  (8 cards, 4 per row)
        self._root.addWidget(SectionHeader(
            "Library Overview",
            "Live counts from your media database",
            QColor(124, 111, 255),
        ))
        self._grid_widget = QWidget()
        self._grid_widget.setStyleSheet("background: transparent;")
        self.grid = QGridLayout(self._grid_widget)
        self.grid.setSpacing(12)
        self._root.addWidget(self._grid_widget)

        stats_meta = [
            ("Movies",           "0", _ACCENTS[0]),
            ("TV Shows",         "0", _ACCENTS[1]),
            ("Episodes",         "0", _ACCENTS[2]),
            ("Unmatched Files",  "0", _ACCENTS[3]),
            ("Missing Episodes", "0", _ACCENTS[4]),
            ("Storage (GB)",     "0", _ACCENTS[5]),
            ("Watch Hours",      "0", _ACCENTS[6]),
            ("Total Files",      "0", _ACCENTS[7]),
        ]
        for i, (label, val, accent) in enumerate(stats_meta):
            card = NeonStatCard(val, label, accent)
            self.grid.addWidget(card, i // 4, i % 4)
            self._stat_cards.append(card)

        # ── Bottom row: donut + breakdown cards
        self._root.addWidget(SectionHeader(
            "Breakdown",
            "Completion, resolution & codec distribution",
            QColor(102, 187, 106),
        ))
        bottom = QHBoxLayout()
        bottom.setSpacing(16)
        self._root.addLayout(bottom)

        # Donut slot
        self._donut_slot = QVBoxLayout()
        donut_wrapper = QWidget()
        donut_wrapper.setStyleSheet("background: transparent;")
        donut_wrapper.setLayout(self._donut_slot)
        bottom.addWidget(donut_wrapper, 2)

        # Resolution card
        self._res_card = GlassCard(accent=QColor(38, 198, 218), accent_h=2)
        res_lay = QVBoxLayout(self._res_card)
        res_lay.setContentsMargins(16, 14, 16, 14)
        res_lay.setSpacing(6)
        res_title = QLabel("Resolution")
        res_title.setStyleSheet("color: #38c6da; font-weight: 700; font-size: 11px; letter-spacing: 0.8px; background: transparent;")
        res_lay.addWidget(res_title)
        self.res_content = QLabel("—")
        self.res_content.setStyleSheet("color: #7070a0; font-size: 12px; background: transparent;")
        self.res_content.setWordWrap(True)
        res_lay.addWidget(self.res_content)
        res_lay.addStretch()

        # Codec card
        self._codec_card = GlassCard(accent=QColor(171, 71, 188), accent_h=2)
        codec_lay = QVBoxLayout(self._codec_card)
        codec_lay.setContentsMargins(16, 14, 16, 14)
        codec_lay.setSpacing(6)
        codec_title = QLabel("Codec")
        codec_title.setStyleSheet("color: #ab47bc; font-weight: 700; font-size: 11px; letter-spacing: 0.8px; background: transparent;")
        codec_lay.addWidget(codec_title)
        self.codec_content = QLabel("—")
        self.codec_content.setStyleSheet("color: #7070a0; font-size: 12px; background: transparent;")
        self.codec_content.setWordWrap(True)
        codec_lay.addWidget(self.codec_content)
        codec_lay.addStretch()

        right_col = QVBoxLayout()
        right_col.setSpacing(12)
        right_col.addWidget(self._res_card)
        right_col.addWidget(self._codec_card)
        bottom.addLayout(right_col, 1)

        # ── Recent additions
        self._root.addWidget(SectionHeader(
            "Recently Added",
            "Last files discovered by the scanner",
            QColor(255, 167, 38),
        ))
        self.recent_card = GlassCard(accent=QColor(255, 167, 38), accent_h=2)
        self.recent_lay = QVBoxLayout(self.recent_card)
        self.recent_lay.setContentsMargins(16, 14, 16, 14)
        self.recent_lay.setSpacing(2)
        self._root.addWidget(self.recent_card)
        self._root.addStretch()

        self.load_rows()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._bg.setGeometry(0, 0, self.width(), self.height())

    def load_rows(self) -> None:
        overview   = self.service.library_overview()
        missing_ep = self.service.missing_episodes_count()
        completion = self.service.shows_completion()

        values = [
            str(overview["total_movies"]),
            str(overview["total_shows"]),
            str(overview["total_episodes"]),
            str(overview["unmatched"]),
            str(missing_ep),
            str(overview["storage_gb"]),
            str(overview["watch_hours"]),
            str(overview["total_files"]),
        ]
        for card, val in zip(self._stat_cards, values):
            card.update_value(val)

        # Donut
        if self._donut_widget is not None:
            self._donut_slot.removeWidget(self._donut_widget)
            self._donut_widget.deleteLater()
        self._donut_widget = _make_donut(
            completion["complete"], completion["partial"], completion["not_started"]
        )
        self._donut_slot.addWidget(self._donut_widget)

        # Breakdowns
        res_rows = self.service.resolution_breakdown()
        lines = []
        for r in res_rows[:8]:
            lines.append(f"●  {r['resolution'] or 'Unknown':<12}  {r['count']}")
        self.res_content.setText("\n".join(lines) or "No data")

        codec_rows = self.service.codec_breakdown()
        lines = []
        for r in codec_rows[:8]:
            lines.append(f"●  {r['video_codec'] or 'Unknown':<12}  {r['count']}")
        self.codec_content.setText("\n".join(lines) or "No data")

        # Recent additions
        while self.recent_lay.count():
            item = self.recent_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for row in self.service.recent_additions(limit=8):
            date_str = str(row["discovered_at"])[:10]
            lbl = QLabel(
                f"<span style='color:#5050a0;font-size:10px'>{date_str}</span>"
                f"&nbsp;&nbsp;"
                f"<span style='color:#9090b0'>{row['file_name']}</span>"
            )
            lbl.setTextFormat(Qt.RichText)
            lbl.setStyleSheet("background: transparent; padding: 3px 0;")
            self.recent_lay.addWidget(lbl)
