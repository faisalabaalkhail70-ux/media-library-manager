import sys
from PySide6.QtWidgets import QApplication

from mlm.app.config import AppConfig
from mlm.app.paths import ensure_app_dirs
from mlm.db.schema import init_database
from mlm.ui.main_window import MainWindow
from mlm.ui.styles import APP_STYLESHEET

def run_app() -> None:
    ensure_app_dirs()
    init_database()

    app = QApplication(sys.argv)
    cfg = AppConfig()
    app.setApplicationName(cfg.app_name)
    app.setStyleSheet(APP_STYLESHEET)

    window = MainWindow()
    window.resize(cfg.window_width, cfg.window_height)
    window.show()

    sys.exit(app.exec())