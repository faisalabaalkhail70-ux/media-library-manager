"""Main application window — redesigned 2026 UI.

Layout
──────
  ┌─────────────────────────────────────────────────────┐
  │  Custom title bar  (drag, min/max/close)            │
  ├──────────┬──────────────────────────────────────────┤
  │          │  Top bar: search + activity              │
  │  Icon    ├──────────────────────────────────────────┤
  │  sidebar │  Page content (QStackedWidget)           │
  │  (60px)  │                                          │
  │          │                                          │
  ├──────────┴──────────────────────────────────────────┤
  │  Status bar                                         │
  └─────────────────────────────────────────────────────┘

Sidebar uses Unicode symbol icons + tooltip labels.
No native window chrome — fully custom frame.
"""
import logging

from PySide6.QtCore import Qt, QPoint, QThread, QSize
from PySide6.QtGui import QFont, QColor, QPainter, QLinearGradient, QBrush, QPen
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow,
    QProgressBar, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget, QApplication,
    QSizePolicy, QGraphicsDropShadowEffect,
)

from mlm.db.repositories.settings_repo import SettingsRepository
from mlm.ui.styles import get_stylesheet
from mlm.ui.global_search import GlobalSearchBar
from mlm.ui.views.dashboard_view    import DashboardView
from mlm.ui.views.scanner_view      import ScannerView
from mlm.ui.views.library_view      import LibraryView
from mlm.ui.views.movies_view       import MoviesView
from mlm.ui.views.shows_view        import ShowsView
from mlm.ui.views.collections_view  import CollectionsView
from mlm.ui.views.watchlist_view    import WatchlistView
from mlm.ui.views.duplicates_view   import DuplicatesView
from mlm.ui.views.rename_view       import RenameView
from mlm.ui.views.health_view       import HealthView
from mlm.ui.views.reports_view      import ReportsView
from mlm.ui.views.settings_view     import SettingsView

log = logging.getLogger(__name__)

# (icon_glyph, tooltip_label, ViewClass)
NAV_ITEMS = [
    ("⌂",  "Dashboard",   DashboardView),
    ("⊕",  "Scanner",     ScannerView),
    ("▤",  "Library",     LibraryView),
    ("▶",  "Movies",      MoviesView),
    ("⊞",  "TV Shows",    ShowsView),
    ("◫",  "Collections", CollectionsView),
    ("♥",  "Watchlist",   WatchlistView),
    ("⊜",  "Duplicates",  DuplicatesView),
    ("✎",  "Rename",      RenameView),
    ("✦",  "Health",      HealthView),
    ("◈",  "Reports",     ReportsView),
    ("⚙",  "Settings",    SettingsView),
]


class _TitleBar(QWidget):
    """Draggable custom title bar with min / max / close."""

    def __init__(self, parent: QMainWindow) -> None:
        super().__init__(parent)
        self._win = parent
        self._drag_pos: QPoint | None = None
        self.setFixedHeight(42)
        self.setObjectName("title_bar")
        self.setAttribute(Qt.WA_StyledBackground, True)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 8, 0)
        lay.setSpacing(0)

        # App name
        self._title = QLabel("Media Library Manager")
        self._title.setObjectName("title_bar_label")
        lay.addWidget(self._title)
        lay.addStretch()

        # Window controls
        for symbol, name, slot in (
            ("─", "min",   parent.showMinimized),
            ("□", "max",   self._toggle_max),
            ("✕", "close", parent.close),
        ):
            btn = QPushButton(symbol)
            btn.setObjectName(f"wc_{name}")
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(slot)
            lay.addWidget(btn)

    def _toggle_max(self) -> None:
        if self._win.isMaximized():
            self._win.showNormal()
        else:
            self._win.showMaximized()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self._win.frameGeometry().topLeft()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.LeftButton:
            self._win.move(e.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        self._toggle_max()
        super().mouseDoubleClickEvent(e)


class _SidebarButton(QPushButton):
    """Icon-only sidebar button with tooltip = section name."""

    def __init__(self, icon: str, tip: str, parent=None) -> None:
        super().__init__(icon, parent)
        self.setObjectName("sidebar_btn")
        self.setCheckable(True)
        self.setFixedSize(52, 52)
        self.setToolTip(tip)
        self.setCursor(Qt.PointingHandCursor)
        f = QFont("Segoe UI Symbol", 18)
        self.setFont(f)


class _GlowWidget(QWidget):
    """Decorative ambient glow blob painted behind the content area."""

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() // 2, self.height() // 3
        r = min(self.width(), self.height()) * 0.70
        grad = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
        grad.setColorAt(0.0, QColor(124, 111, 255, 18))
        grad.setColorAt(0.5, QColor(80,  60, 220, 10))
        grad.setColorAt(1.0, QColor(0,   0,   0,   0))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.NoPen)
        p.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        # Frameless window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setWindowTitle("Media Library Manager")
        self.setMinimumSize(1100, 680)

        settings = SettingsRepository()
        theme = settings.get("ui_theme", "dark")
        QApplication.instance().setStyleSheet(get_stylesheet(theme))

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Custom title bar ───────────────────────────────────────────
        self._title_bar = _TitleBar(self)
        root.addWidget(self._title_bar)

        # ── Alert banner ───────────────────────────────────────────────
        self._alert_banner = QLabel("")
        self._alert_banner.setObjectName("alert_banner")
        self._alert_banner.setAlignment(Qt.AlignCenter)
        self._alert_banner.setVisible(False)
        root.addWidget(self._alert_banner)

        # ── Body (sidebar + content) ───────────────────────────────────
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # ── Icon sidebar ───────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(68)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(8, 16, 8, 16)
        side_layout.setSpacing(4)
        side_layout.setAlignment(Qt.AlignTop)

        # Logo mark
        logo = QLabel("◈")
        logo.setObjectName("sidebar_logo")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedHeight(48)
        side_layout.addWidget(logo)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setObjectName("sidebar_divider")
        div.setFixedHeight(1)
        side_layout.addWidget(div)
        side_layout.addSpacing(8)

        self.stack = QStackedWidget()
        self.nav_buttons: list[QPushButton] = []

        for index, (icon, tip, ViewClass) in enumerate(NAV_ITEMS):
            view = ViewClass()
            self.stack.addWidget(view)
            btn = _SidebarButton(icon, tip)
            btn.clicked.connect(lambda checked, i=index: self.switch_view(i))
            side_layout.addWidget(btn, alignment=Qt.AlignHCenter)
            self.nav_buttons.append(btn)
            # Push Settings to the bottom
            if index == len(NAV_ITEMS) - 2:   # before Settings
                side_layout.addStretch()

        body_layout.addWidget(sidebar)

        # ── Right panel (top bar + glow + content stack) ──────────────
        right_panel = QWidget()
        right_panel.setObjectName("right_panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Top bar: search
        top_bar = QWidget()
        top_bar.setObjectName("top_bar")
        top_bar.setFixedHeight(52)
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(20, 6, 20, 6)
        top_bar_layout.setSpacing(12)

        self._search_bar = GlobalSearchBar(self.stack, self.nav_buttons)
        self._search_bar.setFixedHeight(38)
        top_bar_layout.addWidget(self._search_bar, 1)

        self._activity_label = QLabel("Ready")
        self._activity_label.setObjectName("muted")
        self._activity_label.setStyleSheet("font-size: 11px; min-width: 80px;")
        top_bar_layout.addWidget(self._activity_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedWidth(120)
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        self._progress_bar.setTextVisible(False)
        top_bar_layout.addWidget(self._progress_bar)

        right_layout.addWidget(top_bar)

        # Thin separator
        top_sep = QFrame()
        top_sep.setFrameShape(QFrame.HLine)
        top_sep.setObjectName("top_separator")
        right_layout.addWidget(top_sep)

        # Content stack (with ambient glow behind it)
        content_wrapper = QWidget()
        content_wrapper.setObjectName("content_wrapper")
        cw_layout = QVBoxLayout(content_wrapper)
        cw_layout.setContentsMargins(0, 0, 0, 0)
        cw_layout.setSpacing(0)

        self._glow = _GlowWidget(content_wrapper)
        self._glow.setGeometry(0, 0, 600, 400)
        self._glow.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._glow.lower()

        cw_layout.addWidget(self.stack, 1)
        right_layout.addWidget(content_wrapper, 1)

        body_layout.addWidget(right_panel, 1)
        root.addWidget(body, 1)

        # ── Status bar ─────────────────────────────────────────────────
        status_bar = QFrame()
        status_bar.setObjectName("status_bar")
        status_bar.setFixedHeight(26)
        sb_layout = QHBoxLayout(status_bar)
        sb_layout.setContentsMargins(16, 0, 16, 0)
        sb_layout.setSpacing(0)
        self._status_label = QLabel("Media Library Manager")
        self._status_label.setObjectName("status_label")
        sb_layout.addWidget(self._status_label)
        sb_layout.addStretch()
        ver = QLabel("v1.0.0")
        ver.setObjectName("status_label")
        sb_layout.addWidget(ver)
        root.addWidget(status_bar)

        self._active_workers: int = 0

        density = settings.get("ui_row_density", "comfortable")
        self._row_height = 20 if density == "compact" else 28

        self._check_startup_health()
        self.switch_view(0)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, '_glow'):
            self._glow.setGeometry(0, 0, self.width(), self.height() // 2)

    def _check_startup_health(self) -> None:
        try:
            from mlm.db.connection import get_connection
            with get_connection() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) AS n FROM media_files WHERE is_missing = 1"
                ).fetchone()
            count = row["n"] if row else 0
            if count > 0:
                self._alert_banner.setText(
                    f"⚠  {count} file(s) flagged as missing since last scan. "
                    "Go to Health to review.  [Click to dismiss]"
                )
                self._alert_banner.setVisible(True)
                self._alert_banner.mousePressEvent = lambda _: self._alert_banner.setVisible(False)
        except Exception as exc:
            log.warning("Startup health check failed: %s", exc)

    def track_worker(self, worker: QThread, task_label: str = "Working…") -> None:
        self._active_workers += 1
        self._activity_label.setText(task_label)
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setVisible(True)
        if hasattr(worker, "progress"):
            worker.progress.connect(self._on_worker_progress)
        for signal_name in ("finished", "finished_scan", "finished_build",
                            "finished_apply", "finished_undo", "finished_export",
                            "finished_check", "failed"):
            sig = getattr(worker, signal_name, None)
            if sig is not None:
                sig.connect(lambda *_: self._on_worker_done(task_label))
                break

    def show_alert(self, message: str) -> None:
        self._alert_banner.setText(message + "  [Click to dismiss]")
        self._alert_banner.setVisible(True)
        self._alert_banner.mousePressEvent = lambda _: self._alert_banner.setVisible(False)

    def set_status(self, message: str) -> None:
        self._activity_label.setText(message)

    def _on_worker_progress(self, done: int, total: int) -> None:
        if total > 0:
            self._progress_bar.setRange(0, total)
            self._progress_bar.setValue(done)

    def _on_worker_done(self, task_label: str) -> None:
        self._active_workers = max(0, self._active_workers - 1)
        if self._active_workers == 0:
            self._progress_bar.setVisible(False)
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(0)
            self._activity_label.setText("Ready")

    def switch_view(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        current = self.stack.currentWidget()
        if hasattr(current, "load_rows"):
            current.load_rows()
