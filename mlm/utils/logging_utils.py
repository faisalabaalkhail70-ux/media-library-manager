"""Configure application-wide logging.

Logs always go to the rotating file.  A console (StreamHandler) is added
ONLY when the process is explicitly attached to a terminal — i.e. when the
developer runs ``python main.py`` from a command prompt.  When the app is
launched by double-clicking (no console window), or packaged as a .exe,
no console output is produced.
"""
import logging
import logging.handlers
import sys
from pathlib import Path


def setup_logging(log_file: Path, level: int = logging.INFO) -> None:
    """Set up root logger with a rotating file handler.

    A console handler is attached only when *sys.stderr* is connected to
    a real terminal (i.e. the developer launched from cmd/PowerShell).

    Args:
        log_file: Absolute path to the log file.
        level:    Minimum log level (default INFO — was DEBUG, which was
                  too noisy for normal use).
    """
    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Always write to the rotating file
    fh = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(fh)

    # Only attach a console handler when running in a real terminal.
    # hasattr check covers pythonw.exe / PyInstaller --noconsole where
    # sys.stderr may be None.
    if getattr(sys.stderr, "isatty", lambda: False)():
        ch = logging.StreamHandler(sys.stderr)
        ch.setFormatter(fmt)
        root.addHandler(ch)
