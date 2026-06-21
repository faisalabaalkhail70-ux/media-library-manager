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
    val_lbl.setObjectName("stat_value")
    val_lbl.setAlignment(Qt.AlignCenter)
    val_lbl.setStyleSheet(f"font-size: 26px; font-weight: 700; color: {accent};")

    lbl = QLabel(label)
    lbl.setObjectName("stat_label")
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet("font-size: 11px; color: #aaaaaa;")

    inner.addWidget(val_lbl)
    inner.addWidget(lbl)
    return card


class DashboardView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.service = DashboardService()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)

        # ── Header ────────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("h1")
        header.addWidget(title)
        header.addStretch()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_rows)
        header.addWidget(self.refresh_btn)
        layout.addLayout(header)

        # ── Stats grid ────────────────────────────────────────────
        self.grid = QGridLayout()
        self.grid.setSpacing(12)
        layout.addLayout(self.grid)

        # ── Breakdowns ────────────────────────────────────────────
        breakdown_row = QHBoxLayout()
        breakdown_row.setSpacing(16)

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
        breakdown_row.addWidget(res_box, 1)

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
        breakdown_row.addWidget(codec_box, 1)

        layout.addLayout(breakdown_row)

        # ── Recent Additions ──────────────────────────────────────
        recent_lbl = QLabel("Recently Added")
        recent_lbl.setStyleSheet("font-size: 15px; font-weight: 700;")
        layout.addWidget(recent_lbl)

        self.recent_container = QVBoxLayout()
        self.recent_container.setSpacing(4)
        recent_wrap = QWidget()
        recent_wrap.setLayout(self.recent_container)
        layout.addWidget(recent_wrap)

        layout.addStretch()
        self.load_rows()

    def load_rows(self) -> None:
        overview = self.service.library_overview()
        missing_ep = self.service.missing_episodes_count()

        # ── Rebuild stat cards ────────────────────────────────────
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
            card = _stat_card(label, value, accent)
            self.grid.addWidget(card, i // 4, i % 4)

        # ── Resolution breakdown ──────────────────────────────────
        res_rows = self.service.resolution_breakdown()
        self.res_content.setText(
            "\n".join(f'{r["resolution"]}: {r["count"]}' for r in res_rows[:8])
            or "No data"
        )

        # ── Codec breakdown ───────────────────────────────────────
        codec_rows = self.service.codec_breakdown()
        self.codec_content.setText(
            "\n".join(f'{r["video_codec"]}: {r["count"]}' for r in codec_rows[:8])
            or "No data"
        )

        # ── Recent additions ──────────────────────────────────────
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
