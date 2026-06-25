"""SQLite connection factory with recommended PRAGMAs."""
import sqlite3
import logging
from contextlib import contextmanager
from collections.abc import Generator

from mlm.app.paths import DB_PATH

log = logging.getLogger(__name__)


def create_connection() -> sqlite3.Connection:
    """Open a new SQLite connection with performance and safety PRAGMAs.

    Each QThread must create its own connection; do NOT share connections
    across threads.  check_same_thread is left at the default True value
    so SQLite's built-in guard remains active.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = -32000")  # 32 MB page cache
    conn.execute("PRAGMA temp_store = MEMORY")
    return conn


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager that yields a connection, commits on success, rolls back on error.

    Return type annotated as ``Generator[sqlite3.Connection, None, None]`` so
    that mypy / Pyright can fully type-check callers (issue #12).

    Usage::

        with get_connection() as conn:
            conn.execute("SELECT 1")
    """
    conn = create_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        log.exception("DB transaction rolled back due to unhandled exception")
        raise
    finally:
        conn.close()
