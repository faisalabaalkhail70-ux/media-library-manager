"""Main application window with sidebar navigation and a global activity bar."""
import logging

from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow,
    QProgressBar, QPushButton, QSizePolicy,
    QStackedWidget, QVBoxLayout, QWidget,
)

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
    """Top-level window: sidebar + stacked content area + global activity bar.

    The activity bar at the bottom shows a progress bar and status label
    whenever any background worker is active.  Views register their workers
    by calling ``MainWindow.track_worker(worker, label)``.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Media Library Manager")

        central = QWidget()
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Main area (sidebar + stack) ───────────────────────────
        main_area = QWidget()
        main_layout = QHBoxLayout(main_area)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────
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

        self.stack = QStackedWidget()
        self.nav_buttons: list[QPushButton] = []

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

        # ── Global activity bar (bottom) ──────────────────────────
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

        outer.addWidget(main_area, 1)
        outer.addWidget(activity_bar)

        self._active_workers: int = 0
        self.switch_view(0)

    # ── Public API for views ──────────────────────────────────────

    def track_worker(self, worker: QThread, task_label: str = "Working…") -> None:
        """Connect *worker* signals to the global activity bar.

        Call this from any view immediately after creating a QThread worker::

            self.worker = ScanWorker(...)
            self.window().track_worker(self.worker, "Scanning…")
            self.worker.start()

        The progress bar shows indefinite animation while the worker runs
        and disappears automatically when it finishes or fails.
        If the worker emits ``progress(int done, int total)`` the bar switches
        to determinate mode.
        """
        self._active_workers += 1
        self._activity_label.setText(task_label)
        self._progress_bar.setRange(0, 0)   # indeterminate (spinner-style)
        self._progress_bar.setVisible(True)
        log.debug("Activity bar: started '%s' (%d active)", task_label, self._active_workers)

        # Wire determinate progress if the worker supports it
        if hasattr(worker, "progress"):
            worker.progress.connect(self._on_worker_progress)

        # Wire finish / failure to hide the bar
        for signal_name in ("finished", "finished_scan", "finished_build",
                            "finished_apply", "finished_undo", "finished_export",
                            "failed"):
            sig = getattr(worker, signal_name, None)
            if sig is not None:
                sig.connect(lambda *_: self._on_worker_done(task_label))
                break  # only connect the first matching signal

    def set_status(self, message: str) -> None:
        """Update the activity bar label from any view."""
        self._activity_label.setText(message)

    # ── Private slots ─────────────────────────────────────────────

    def _on_worker_progress(self, done: int, total: int) -> None:
        if total > 0:
            self._progress_bar.setRange(0, total)
            self._progress_bar.setValue(done)

    def _on_worker_done(self, task_label: str) -> None:
        self._active_workers = max(0, self._active_workers - 1)
        log.debug("Activity bar: finished '%s' (%d active)", task_label, self._active_workers)
        if self._active_workers == 0:
            self._progress_bar.setVisible(False)
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(0)
            self._activity_label.setText("Ready")

    # ── Navigation ────────────────────────────────────────────────

    def switch_view(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        current = self.stack.currentWidget()
        if hasattr(current, "load_rows"):
            current.load_rows()
