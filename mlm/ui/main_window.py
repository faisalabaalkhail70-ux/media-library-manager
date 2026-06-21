from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QFrame, QStackedWidget
)
from PySide6.QtCore import Qt

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


NAV_ITEMS = [
    ("🏠  Dashboard",   DashboardView),
    ("📂  Scanner",     ScannerView),
    ("📚  Library",     LibraryView),
    ("🎬  Movies",      MoviesView),
    ("📺  TV Shows",    ShowsView),
    ("🔍  Duplicates",  DuplicatesView),
    ("✏️  Rename",      RenameView),
    ("🩺  Health",      HealthView),
    ("📊  Reports",     ReportsView),
    ("⚙️  Settings",    SettingsView),
]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Media Library Manager")
        self.resize(1400, 860)

        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

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

        # ── Stack + Nav Buttons ───────────────────────────────────
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

        # ── Version label ─────────────────────────────────────────
        version_lbl = QLabel("v1.0.0")
        version_lbl.setObjectName("muted")
        version_lbl.setAlignment(Qt.AlignCenter)
        version_lbl.setStyleSheet("font-size: 11px;")
        side_layout.addWidget(version_lbl)

        root.addWidget(sidebar)
        root.addWidget(self.stack, 1)

        self.switch_view(0)

    def switch_view(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        current = self.stack.currentWidget()
        if hasattr(current, "load_rows"):
            current.load_rows()