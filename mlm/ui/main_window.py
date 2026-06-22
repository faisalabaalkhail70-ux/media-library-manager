"""Main application window — sidebar + stacked content + global search + activity bar."""
import logging

from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow,
    QProgressBar, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget, QApplication
)

from mlm.db.repositories.settings_repo import SettingsRepository
from mlm.ui.styles import get_stylesheet
from mlm.ui.global_search import GlobalSearchBar
from mlm.ui.views.dashboard_view   import DashboardView
from mlm.ui.views.scanner_view     import ScannerView
from mlm.ui.views.library_view     import LibraryView
from mlm.ui.views.movies_view      import MoviesView
from mlm.ui.views.shows_view       import ShowsView
from mlm.ui.views.duplicates_view  import DuplicatesView
from mlm.ui.views.rename_view      import RenameView
from mlm.ui.views.health_view      import HealthView
from mlm.ui.views.reports_view     import ReportsView
from mlm.ui.views.settings_view    import SettingsView

log = logging.getLogger(__name__)

NAV_ITEMS = [
    ("\U0001f3e0  Dashboard",   DashboardView),
    ("\U0001f4c2  Scanner",     ScannerView),
    ("\U0001f4da  Library",     LibraryView),
    ("\U0001f3ac  Movies",      MoviesView),
    ("\U0001f4fa  TV Shows",    ShowsView),
    ("\U0001f50d  Duplicates",  DuplicatesView),
    ("\u270f\ufe0f  Rename",      RenameView),
    ("\U0001fa7a  Health",      HealthView),
    ("\U0001f4ca  Reports",     ReportsView),
    ("\u2699\ufe0f  Settings",    SettingsView),
]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Media Library Manager")

        settings = SettingsRepository()
        theme = settings.get("ui_theme", "dark")
        QApplication.instance().setStyleSheet(get_stylesheet(theme))

        central = QWidget()
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Health alert banner ─────────────────────────────────────────
        self._alert_banner = QLabel("")
        self._alert_banner.setObjectName("alert_banner")
        self._alert_banner.setAlignment(Qt.AlignCenter)
        self._alert_banner.setVisible(False)
        outer.addWidget(self._alert_banner)

        # ── Global search bar ─────────────────────────────────────────
        # Built after stack so we can pass nav_buttons to it
        self.stack = QStackedWidget()
        self.nav_buttons: list[QPushButton] = []

        # ── Main area (sidebar + stack) ────────────────────────────────
        main_area = QWidget()
        main_layout = QHBoxLayout(main_area)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ────────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 20, 12, 16)
        side_layout.setSpacing(4)

        logo = QLabel("Media Library\nManager")
        logo.setObjectName("h1")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("font-size: 15px; padding-bottom: 12px;")
        side_layout.addWidget(logo)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: #333; margin-bottom: 8px;")
        side_layout.addWidget(divider)

        for index, (label, ViewClass) in enumerate(NAV_ITEMS):
            view = ViewClass()
            self.stack.addWidget(view)
            btn = QPushButton(label)
            btn.setObjectName("sidebar_btn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=index: self.switch_view(i))
            side_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        side_layout.addStretch()
        version_lbl = QLabel("v1.0.0")
        version_lbl.setObjectName("muted")
        version_lbl.setAlignment(Qt.AlignCenter)
        version_lbl.setStyleSheet("font-size: 11px;")
        side_layout.addWidget(version_lbl)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stack, 1)

        # Now build the search bar (needs stack + nav_buttons)
        self._search_bar = GlobalSearchBar(self.stack, self.nav_buttons)
        self._search_bar.setFixedHeight(44)
        self._search_bar.setStyleSheet(
            "background: #1a1a1a; border-bottom: 1px solid #2c2c2c;"
        )

        outer.addWidget(self._search_bar)
        outer.addWidget(main_area, 1)

        # ── Global activity bar ─────────────────────────────────────────
        activity_bar = QFrame()
        activity_bar.setObjectName("activity_bar")
        activity_bar.setFixedHeight(32)
        activity_bar.setStyleSheet(
            "#activity_bar { background: #1a1a2e; border-top: 1px solid #2a2a3e; }"
        )
        bar_layout = QHBoxLayout(activity_bar)
        bar_layout.setContentsMargins(12, 0, 12, 0)
        bar_layout.setSpacing(10)

        self._activity_label = QLabel("Ready")
        self._activity_label.setObjectName("muted")
        self._activity_label.setStyleSheet("font-size: 11px;")

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedWidth(200)
        self._progress_bar.setFixedHeight(14)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(
            "QProgressBar { background: #2a2a3e; border-radius: 7px; }"
            "QProgressBar::chunk { background: #6c63ff; border-radius: 7px; }"
        )

        bar_layout.addWidget(self._activity_label)
        bar_layout.addStretch()
        bar_layout.addWidget(self._progress_bar)
        outer.addWidget(activity_bar)

        self._active_workers: int = 0

        density = settings.get("ui_row_density", "comfortable")
        self._row_height = 20 if density == "compact" else 28

        self._check_startup_health()
        self.switch_view(0)

    # ── Startup health check ─────────────────────────────────────────

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
                    f"\u26a0\ufe0f  {count} file(s) flagged as missing since last scan. "
                    "Go to Health to review.  [Click to dismiss]"
                )
                self._alert_banner.setVisible(True)
                self._alert_banner.mousePressEvent = lambda _: self._alert_banner.setVisible(False)
        except Exception as exc:
            log.warning("Startup health check failed: %s", exc)

    # ── Public API ──────────────────────────────────────────────

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

    # ── Private slots ───────────────────────────────────────────

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

    # ── Navigation ──────────────────────────────────────────────

    def switch_view(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        current = self.stack.currentWidget()
        if hasattr(current, "load_rows"):
            current.load_rows()
