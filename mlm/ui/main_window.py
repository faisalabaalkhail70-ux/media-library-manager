from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QFrame, QStackedWidget
)
from PySide6.QtCore import Qt

from mlm.ui.views.dashboard_view import DashboardView
from mlm.ui.views.scanner_view import ScannerView
from mlm.ui.views.library_view import LibraryView
from mlm.ui.views.settings_view import SettingsView

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Media Library Manager")
        self.resize(1400, 850)

        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 20, 12, 20)
        side_layout.setSpacing(8)

        logo = QLabel("Media Library\nManager")
        logo.setObjectName("h1")
        logo.setAlignment(Qt.AlignCenter)
        side_layout.addWidget(logo)

        self.stack = QStackedWidget()
        self.views = [
            DashboardView(),
            ScannerView(),
            LibraryView(),
            SettingsView(),
        ]

        for view in self.views:
            self.stack.addWidget(view)

        self.nav_buttons = []
        for index, label in enumerate(["Dashboard", "Scanner", "Library", "Settings"]):
            btn = QPushButton(label)
            btn.setObjectName("sidebar_btn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=index: self.switch_view(i))
            side_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        side_layout.addStretch()

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