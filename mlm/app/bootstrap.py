"""Application bootstrap: initialise dirs, DB, logging, then launch Qt window."""
import sys
import logging

from PySide6.QtWidgets import QApplication

from mlm.app.config import AppConfig
from mlm.app.paths import ensure_app_dirs, LOG_DIR
from mlm.db.schema import init_database
from mlm.ui.main_window import MainWindow
from mlm.ui.styles import APP_STYLESHEET
from mlm.utils.logging_utils import setup_logging


def run_app() -> None:
    """Entry point: set up infrastructure, then run the Qt event loop."""
    ensure_app_dirs()
    setup_logging(LOG_DIR / "atlas.log")

    log = logging.getLogger(__name__)
    log.info("Atlas starting up")

    init_database()

    app = QApplication(sys.argv)
    cfg = AppConfig()
    app.setApplicationName(cfg.app_name)
    app.setStyleSheet(APP_STYLESHEET)

    window = MainWindow()
    window.resize(cfg.window_width, cfg.window_height)
    window.show()

    log.info("Qt event loop started")
    sys.exit(app.exec())
