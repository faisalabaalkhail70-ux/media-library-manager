"""SQLite connection context manager.

Changes in v1.1
---------------
* Exception is now bound to `exc` in the rollback handler so the log
  message includes the actual exception string (issue #13).
"""
from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from mlm.app.config import AppConfig

log = logging.getLogger(__name__)

_config  = AppConfig()
_DB_PATH: Path = _config.db_path


@contextmanager
def get_connection():
    """Yield a SQLite connection with WAL mode and row-dict factory.

    Commits on clean exit, rolls back and re-raises on any exception.
    """
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        log.exception("DB transaction rolled back: %s", exc)
        raise
    finally:
        conn.close()
