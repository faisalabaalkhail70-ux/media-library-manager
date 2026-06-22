"""Configure application-wide logging to both console and a rotating file."""
import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_file: Path, level: int = logging.DEBUG) -> None:
    """Set up root logger with console + rotating-file handlers.

    Args:
        log_file: Absolute path to the log file.
        level:    Minimum log level (default DEBUG).
    """
    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file — max 5 MB × 3 backups
    fh = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setFormatter(fmt)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(fh)
    root.addHandler(ch)
