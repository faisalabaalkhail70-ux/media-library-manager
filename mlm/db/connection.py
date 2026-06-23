"""SQLite connection factory with recommended PRAGMAs.

Also provides ``run_subprocess_safe``, a non-blocking Popen wrapper
used by ``FFprobeClient`` to avoid calling ``subprocess.run`` (which
blocks the calling thread for the full process lifetime).
"""
import subprocess
import sqlite3
import logging
from contextlib import contextmanager

from mlm.app.paths import DB_PATH

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

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
def get_connection():
    """Yield a connection, commit on success, roll back and re-raise on error."""
    conn = create_connection()
    try:
        yield conn
        conn.commit()
    except Exception as exc:
        conn.rollback()
        log.exception("DB transaction rolled back: %s", exc)
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Subprocess helper
# ---------------------------------------------------------------------------

def run_subprocess_safe(
    cmd: list[str],
    timeout: int = 30,
    running_fn=None,
) -> str:
    """Run *cmd* via Popen and return its stdout as a string.

    Unlike ``subprocess.run``, this function:
    - Polls the child process in short intervals so the calling thread
      is not blocked for the full duration.
    - Respects an optional *running_fn* callable: if it returns ``False``
      the child process is killed and ``InterruptedError`` is raised.
    - Raises ``RuntimeError`` on timeout and
      ``subprocess.CalledProcessError`` on non-zero exit code.

    Args:
        cmd:        Command list (e.g. ``["ffprobe", "-v", "quiet", ...]``).
        timeout:    Maximum seconds to wait before killing the process.
        running_fn: Optional ``() -> bool`` polled every 50 ms.  Return
                    ``False`` to abort.

    Returns:
        The process\'s stdout decoded as UTF-8 (with lossy replacement).
    """
    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
    ) as proc:
        import time
        deadline = time.monotonic() + timeout
        while proc.poll() is None:
            if running_fn is not None and not running_fn():
                proc.kill()
                raise InterruptedError(f"Process killed: worker stopped during {cmd[0]}")
            if time.monotonic() > deadline:
                proc.kill()
                raise RuntimeError(
                    f"{cmd[0]} timed out after {timeout}s (cmd={' '.join(cmd[:4])}...)"
                )
            time.sleep(0.05)

        stdout = proc.stdout.read() if proc.stdout else ""
        if proc.returncode != 0:
            stderr = proc.stderr.read() if proc.stderr else ""
            raise subprocess.CalledProcessError(
                proc.returncode, cmd, output=stdout, stderr=stderr
            )
        return stdout
