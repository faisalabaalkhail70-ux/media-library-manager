"""Main application window — 2026 cinematic redesign.

Layout
──────
  ┌─────────────────────────────────────────────────────┐
  │  Custom title bar  (drag / min / max / close)       │
  ├─────────────┬────────────────────────────────────┤
  │            │  Top bar: breadcrumb + search + status   │
  │  Hero       ├──────────────────────────────────────────────┤
  │  sidebar   │  Page content (QStackedWidget)           │
  │  icon+label │                                          │
  │  (180 px)  │                                          │
  ├─────────────┴────────────────────────────────────┤
  │  Status bar                                           │
  └─────────────────────────────────────────────────────┘

Sidebar: painted hero gradient with icon + label nav items.
Each nav item is a 180px-wide button showing icon + section name.
"""
import logging

from PySide6.QtCore import Qt, QPoint, QThread, QRect, QRectF, QSize
from PySide6.QtGui import (
    QColor, QPainter, QLinearGradient, QRadialGradient,
    QBrush, QPen, QPainterPath, QFont, QFontMetrics
)
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

# (icon_glyph, label, ViewClass)
NAV_ITEMS = [
    ("⌂",  "Dashboard",    DashboardView),
    ("⊕",  "Scanner",      ScannerView),
    ("▤",  "Library",      LibraryView),
    ("▶",  "Movies",       MoviesView),
    ("⊞",  "TV Shows",     ShowsView),
    ("◫",  "Collections",  CollectionsView),
    ("♥",  "Watchlist",    WatchlistView),
    ("⊜",  "Duplicates",   DuplicatesView),
    ("✎",  "Rename",       RenameView),
    ("✦",  "Health",       HealthView),
    ("◈",  "Reports",      ReportsView),
    ("⚙",  "Settings",     SettingsView),
]

_ACCENT      = QColor(124, 111, 255)
_SIDEBAR_BG1 = QColor(8,   6,  22)     # top of sidebar gradient
_SIDEBAR_BG2 = QColor(12, 10, 28)     # bottom
_ITEM_H      = 42


# ──────────────────────────────────────────────────────────────────────
class _HeroSidebar(QWidget):
    """
    Fully custom-painted sidebar.
    Draws its own gradient background, logo mark, divider,
    and all nav items — no stylesheet needed.
    """
    _nav_clicked = None   # injected by MainWindow

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(180)
        self._active = 0
        self._hovered = -1
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        # reserve top for logo + divider
        self._nav_top = 90
        self._item_rects: list[QRect] = []

    def set_active(self, index: int) -> None:
        self._active = index
        self.update()

    def _item_rect(self, i: int) -> QRect:
        y = self._nav_top + i * (_ITEM_H + 2)
        return QRect(10, y, self.width() - 20, _ITEM_H)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()

        # ─ Background gradient
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0, _SIDEBAR_BG1)
        bg.setColorAt(1, _SIDEBAR_BG2)
        p.fillRect(0, 0, w, h, bg)

        # ─ Right border
        p.setPen(QPen(QColor(255, 255, 255, 12), 1))
        p.drawLine(w - 1, 0, w - 1, h)

        # ─ Logo area: large glowing diamond
        lf = QFont("Segoe UI Symbol", 24)
        p.setFont(lf)
        logo_grad = QLinearGradient(0, 18, w, 50)
        logo_grad.setColorAt(0, QColor(200, 195, 255))
        logo_grad.setColorAt(1, _ACCENT)
        pen = QPen()
        pen.setBrush(QBrush(logo_grad))
        p.setPen(pen)
        p.drawText(QRect(0, 14, w, 42), Qt.AlignCenter, "◈")

        # App name
        af = QFont("Segoe UI", 8, QFont.Bold)
        p.setFont(af)
        p.setPen(QColor(80, 75, 120))
        p.drawText(QRect(0, 52, w, 16), Qt.AlignCenter, "MEDIA LIBRARY")

        # Divider
        p.setPen(QPen(QColor(255, 255, 255, 10), 1))
        p.drawLine(20, 76, w - 20, 76)

        # ─ Nav items
        icon_font  = QFont("Segoe UI Symbol", 14)
        label_font = QFont("Segoe UI", 9)
        label_font.setWeight(QFont.Medium)

        n = len(NAV_ITEMS)
        for i, (icon, label, _) in enumerate(NAV_ITEMS):
            rect = self._item_rect(i)
            is_active  = (i == self._active)
            is_hovered = (i == self._hovered)
            is_settings = (i == n - 1)

            # Push Settings to near-bottom
            if is_settings:
                rect = QRect(10, h - _ITEM_H - 14, w - 20, _ITEM_H)

            # Active background pill
            if is_active:
                pill = QPainterPath()
                pill.addRoundedRect(QRectF(rect), 10, 10)
                fill = QColor(_ACCENT)
                fill.setAlpha(40)
                p.fillPath(pill, fill)
                # Left accent bar
                bar = QPainterPath()
                bar.addRoundedRect(QRectF(rect.left(), rect.top() + 6, 3, rect.height() - 12), 1.5, 1.5)
                p.fillPath(bar, _ACCENT)
            elif is_hovered:
                pill = QPainterPath()
                pill.addRoundedRect(QRectF(rect), 10, 10)
                p.fillPath(pill, QColor(255, 255, 255, 8))

            # Icon
            p.setFont(icon_font)
            if is_active:
                p.setPen(_ACCENT)
            elif is_hovered:
                p.setPen(QColor(200, 200, 230))
            else:
                p.setPen(QColor(70, 68, 100))
            p.drawText(QRect(rect.left() + 10, rect.top(), 28, rect.height()), Qt.AlignVCenter | Qt.AlignLeft, icon)

            # Label
            p.setFont(label_font)
            if is_active:
                p.setPen(QColor(230, 225, 255))
            elif is_hovered:
                p.setPen(QColor(180, 178, 210))
            else:
                p.setPen(QColor(70, 68, 100))
            p.drawText(QRect(rect.left() + 42, rect.top(), rect.width() - 44, rect.height()), Qt.AlignVCenter | Qt.AlignLeft, label)

    def mouseMoveEvent(self, e):
        n = len(NAV_ITEMS)
        hit = -1
        for i in range(n):
            rect = self._item_rect(i)
            if i == n - 1:
                rect = QRect(10, self.height() - _ITEM_H - 14, self.width() - 20, _ITEM_H)
            if rect.contains(e.position().toPoint()):
                hit = i
                break
        if hit != self._hovered:
            self._hovered = hit
            self.update()
        super().mouseMoveEvent(e)

    def leaveEvent(self, e):
        self._hovered = -1
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        n = len(NAV_ITEMS)
        for i in range(n):
            rect = self._item_rect(i)
            if i == n - 1:
                rect = QRect(10, self.height() - _ITEM_H - 14, self.width() - 20, _ITEM_H)
            if rect.contains(e.position().toPoint()):
                if self._nav_clicked:
                    self._nav_clicked(i)
                break
        super().mousePressEvent(e)


# ──────────────────────────────────────────────────────────────────────
class _TitleBar(QWidget):
    """Frameless draggable title bar."""
    def __init__(self, win: QMainWindow) -> None:
        super().__init__(win)
        self._win = win
        self._drag_pos: QPoint | None = None
        self.setFixedHeight(40)
        self.setAttribute(Qt.WA_StyledBackground)
        self.setObjectName("title_bar")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 8, 0)
        lay.setSpacing(0)

        title = QLabel("Media Library Manager")
        title.setObjectName("title_bar_label")
        lay.addWidget(title)
        lay.addStretch()

        for sym, name, slot in (
            ("─", "min",   win.showMinimized),
            ("□", "max",   self._toggle_max),
            ("✕", "close", win.close),
        ):
            btn = QPushButton(sym)
            btn.setObjectName(f"wc_{name}")
            btn.setFixedSize(34, 34)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(slot)
            lay.addWidget(btn)

    def _toggle_max(self):
        self._win.showNormal() if self._win.isMaximized() else self._win.showMaximized()

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


# ──────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
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

        # Title bar
        self._title_bar = _TitleBar(self)
        root.addWidget(self._title_bar)

        # Alert banner
        self._alert_banner = QLabel("")
        self._alert_banner.setObjectName("alert_banner")
        self._alert_banner.setAlignment(Qt.AlignCenter)
        self._alert_banner.setVisible(False)
        root.addWidget(self._alert_banner)

        # Body
        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)

        # Hero sidebar
        self._sidebar = _HeroSidebar()
        self._sidebar._nav_clicked = self.switch_view
        body_lay.addWidget(self._sidebar)

        # Right panel
        right = QWidget()
        right.setObjectName("right_panel")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        # Top bar
        top_bar = QWidget()
        top_bar.setObjectName("top_bar")
        top_bar.setFixedHeight(50)
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(20, 6, 20, 6)
        tb_lay.setSpacing(14)

        # Breadcrumb label (updates with active section)
        self._breadcrumb = QLabel("Dashboard")
        self._breadcrumb.setStyleSheet(
            "color: #30304a; font-size: 11px; font-weight: 600;"
            "letter-spacing: 0.5px; background: transparent;"
        )
        tb_lay.addWidget(self._breadcrumb)

        tb_lay.addStretch()

        # Stack & nav buttons (nav_buttons kept for GlobalSearchBar compatibility)
        self.stack = QStackedWidget()
        self.nav_buttons: list[QPushButton] = []
        for index, (icon, label, ViewClass) in enumerate(NAV_ITEMS):
            view = ViewClass()
            self.stack.addWidget(view)
            # Dummy invisible button so GlobalSearchBar still works
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setVisible(False)
            self.nav_buttons.append(btn)

        self._search_bar = GlobalSearchBar(self.stack, self.nav_buttons)
        self._search_bar.setFixedHeight(36)
        tb_lay.addWidget(self._search_bar, 1)

        self._activity_label = QLabel("Ready")
        self._activity_label.setStyleSheet(
            "color: #303048; font-size: 11px; background: transparent;"
        )
        tb_lay.addWidget(self._activity_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedWidth(100)
        self._progress_bar.setFixedHeight(3)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setVisible(False)
        self._progress_bar.setTextVisible(False)
        tb_lay.addWidget(self._progress_bar)

        right_lay.addWidget(top_bar)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("top_separator")
        right_lay.addWidget(sep)

        right_lay.addWidget(self.stack, 1)
        body_lay.addWidget(right, 1)
        root.addWidget(body, 1)

        # Status bar
        status = QFrame()
        status.setObjectName("status_bar")
        status.setFixedHeight(24)
        sb_lay = QHBoxLayout(status)
        sb_lay.setContentsMargins(16, 0, 16, 0)
        self._status_label = QLabel("Media Library Manager")
        self._status_label.setObjectName("status_label")
        sb_lay.addWidget(self._status_label)
        sb_lay.addStretch()
        sb_lay.addWidget(QLabel("v1.0.0"))
        root.addWidget(status)

        self._active_workers = 0
        density = settings.get("ui_row_density", "comfortable")
        self._row_height = 20 if density == "compact" else 28

        self._check_startup_health()
        self.switch_view(0)

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
                    f"⚠  {count} missing file(s) since last scan — check Health  [click to dismiss]"
                )
                self._alert_banner.setVisible(True)
                self._alert_banner.mousePressEvent = lambda _: self._alert_banner.setVisible(False)
        except Exception as exc:
            log.warning("Startup health check: %s", exc)

    def track_worker(self, worker: QThread, task_label: str = "Working…") -> None:
        self._active_workers += 1
        self._activity_label.setText(task_label)
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setVisible(True)
        if hasattr(worker, "progress"):
            worker.progress.connect(self._on_worker_progress)
        for sig_name in ("finished", "finished_scan", "finished_build",
                         "finished_apply", "finished_undo", "finished_export",
                         "finished_check", "failed"):
            sig = getattr(worker, sig_name, None)
            if sig is not None:
                sig.connect(lambda *_: self._on_worker_done())
                break

    def show_alert(self, message: str) -> None:
        self._alert_banner.setText(message + "  [click to dismiss]")
        self._alert_banner.setVisible(True)
        self._alert_banner.mousePressEvent = lambda _: self._alert_banner.setVisible(False)

    def set_status(self, message: str) -> None:
        self._activity_label.setText(message)

    def _on_worker_progress(self, done: int, total: int) -> None:
        if total > 0:
            self._progress_bar.setRange(0, total)
            self._progress_bar.setValue(done)

    def _on_worker_done(self) -> None:
        self._active_workers = max(0, self._active_workers - 1)
        if self._active_workers == 0:
            self._progress_bar.setVisible(False)
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(0)
            self._activity_label.setText("Ready")

    def switch_view(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self._sidebar.set_active(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        _, label, _ = NAV_ITEMS[index]
        self._breadcrumb.setText(label.upper())
        current = self.stack.currentWidget()
        if hasattr(current, "load_rows"):
            current.load_rows()
