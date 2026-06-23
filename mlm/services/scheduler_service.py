"""E-3 — APScheduler-based task scheduler service.

Uses APScheduler's BackgroundScheduler with a SQLAlchemyJobStore backed
by the app's SQLite database.  All job definitions are also mirrored into
the ``scheduled_tasks`` table so the UI can read them without touching the
APScheduler internals.

Supported task types
--------------------
``scan``          Run a library scan for every enabled directory.
``health``        Run a health scan of all files.
``snapshot``      Take a library snapshot.
``restructure``   Run folder restructuring on all enabled directories.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import (
    EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, JobExecutionEvent
)

from mlm.db.connection import get_connection
from mlm.app.config import AppConfig

log = logging.getLogger(__name__)

_cfg = AppConfig()
_DB_URL = f"sqlite:///{_cfg.db_path}"


# ---------------------------------------------------------------------------
# Task callables (run in APScheduler's thread pool)
# ---------------------------------------------------------------------------

def _task_scan() -> None:
    """Scan every enabled directory."""
    from mlm.services.scan_service import ScanService
    from mlm.db.connection import get_connection as gc
    with gc() as conn:
        dirs = conn.execute(
            "SELECT id, path FROM directories WHERE is_enabled = 1"
        ).fetchall()
    svc = ScanService()
    for row in dirs:
        try:
            svc.scan_directory(row["id"], row["path"])
        except Exception as exc:  # noqa: BLE001
            log.error("Scheduled scan failed for %s: %s", row["path"], exc)


def _task_health() -> None:
    from mlm.services.health_service import HealthService
    HealthService().run_health_scan()


def _task_snapshot() -> None:
    from mlm.services.snapshot_service import SnapshotService
    label = f"auto-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}"
    SnapshotService().take_snapshot(label=label)


def _task_restructure() -> None:
    from mlm.services.folder_restructure_service import FolderRestructureService
    from mlm.db.connection import get_connection as gc
    with gc() as conn:
        dirs = conn.execute(
            "SELECT id FROM directories WHERE is_enabled = 1"
        ).fetchall()
    svc = FolderRestructureService()
    for row in dirs:
        try:
            svc.restructure_directory(row["id"], dry_run=False)
        except Exception as exc:  # noqa: BLE001
            log.error("Scheduled restructure failed for dir %d: %s", row["id"], exc)


_TASK_FN = {
    "scan":        _task_scan,
    "health":      _task_health,
    "snapshot":    _task_snapshot,
    "restructure": _task_restructure,
}


# ---------------------------------------------------------------------------
# SchedulerService
# ---------------------------------------------------------------------------

class SchedulerService:
    """Singleton-style wrapper around APScheduler BackgroundScheduler.

    Call ``start()`` once at application startup and ``shutdown()`` at exit.
    """

    def __init__(self) -> None:
        jobstores = {"default": SQLAlchemyJobStore(url=_DB_URL, tablename="apscheduler_jobs")}
        self._sched = BackgroundScheduler(jobstores=jobstores, timezone="UTC")
        self._sched.add_listener(self._on_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the scheduler.  Safe to call multiple times."""
        if not self._sched.running:
            self._sync_from_db()     # restore user-configured jobs
            self._sched.start()
            log.info("Scheduler started (%d jobs)", len(self._sched.get_jobs()))

    def shutdown(self) -> None:
        if self._sched.running:
            self._sched.shutdown(wait=False)
            log.info("Scheduler shut down")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_interval_job(
        self,
        task_type: str,
        interval_minutes: int,
        job_id: str | None = None,
    ) -> str:
        """Add or replace an interval-based job."""
        if task_type not in _TASK_FN:
            raise ValueError(f"Unknown task type: {task_type!r}")
        job_id = job_id or f"{task_type}_interval"
        fn = _TASK_FN[task_type]
        trigger = IntervalTrigger(minutes=interval_minutes)
        self._sched.add_job(
            fn, trigger, id=job_id, replace_existing=True,
            misfire_grace_time=120,
        )
        self._upsert_db_record(
            job_id=job_id,
            task_type=task_type,
            cron_expr=None,
            interval_min=interval_minutes,
        )
        log.info("Scheduled %s every %d min (id=%s)", task_type, interval_minutes, job_id)
        return job_id

    def add_cron_job(
        self,
        task_type: str,
        cron_expr: str,
        job_id: str | None = None,
    ) -> str:
        """Add or replace a cron-based job.  *cron_expr* uses 5-field UNIX cron."""
        if task_type not in _TASK_FN:
            raise ValueError(f"Unknown task type: {task_type!r}")
        job_id = job_id or f"{task_type}_cron"
        fn = _TASK_FN[task_type]
        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValueError(f"cron_expr must have 5 fields, got: {cron_expr!r}")
        minute, hour, day, month, day_of_week = parts
        trigger = CronTrigger(
            minute=minute, hour=hour, day=day,
            month=month, day_of_week=day_of_week,
        )
        self._sched.add_job(
            fn, trigger, id=job_id, replace_existing=True,
            misfire_grace_time=120,
        )
        self._upsert_db_record(
            job_id=job_id,
            task_type=task_type,
            cron_expr=cron_expr,
            interval_min=None,
        )
        log.info("Scheduled %s cron=%r (id=%s)", task_type, cron_expr, job_id)
        return job_id

    def remove_job(self, job_id: str) -> None:
        try:
            self._sched.remove_job(job_id)
        except Exception:  # noqa: BLE001
            pass
        with get_connection() as conn:
            conn.execute("DELETE FROM scheduled_tasks WHERE job_id = ?", (job_id,))

    def enable_job(self, job_id: str) -> None:
        self._sched.resume_job(job_id)
        with get_connection() as conn:
            conn.execute(
                "UPDATE scheduled_tasks SET is_enabled = 1 WHERE job_id = ?",
                (job_id,),
            )

    def disable_job(self, job_id: str) -> None:
        self._sched.pause_job(job_id)
        with get_connection() as conn:
            conn.execute(
                "UPDATE scheduled_tasks SET is_enabled = 0 WHERE job_id = ?",
                (job_id,),
            )

    def list_jobs(self) -> list[dict[str, Any]]:
        """Return UI-friendly job rows merged from APScheduler + DB."""
        with get_connection() as conn:
            db_rows = {
                r["job_id"]: dict(r)
                for r in conn.execute("SELECT * FROM scheduled_tasks").fetchall()
            }
        jobs = []
        for job in self._sched.get_jobs():
            db_r = db_rows.get(job.id, {})
            next_run = job.next_run_time
            jobs.append({
                "job_id":       job.id,
                "task_type":    db_r.get("task_type", "unknown"),
                "cron_expr":    db_r.get("cron_expr"),
                "interval_min": db_r.get("interval_min"),
                "is_enabled":   db_r.get("is_enabled", 1),
                "last_run_at":  db_r.get("last_run_at"),
                "last_status":  db_r.get("last_status"),
                "next_run_at":  next_run.isoformat() if next_run else None,
            })
        return jobs

    def run_now(self, job_id: str) -> None:
        """Execute a job immediately (bypasses trigger)."""
        job = self._sched.get_job(job_id)
        if job is None:
            raise KeyError(f"Job not found: {job_id!r}")
        job.func()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _on_job_event(self, event: JobExecutionEvent) -> None:
        status = "error" if event.exception else "ok"
        now = datetime.now(timezone.utc).isoformat()
        job = self._sched.get_job(event.job_id)
        next_run = job.next_run_time.isoformat() if (job and job.next_run_time) else None
        try:
            with get_connection() as conn:
                conn.execute(
                    "UPDATE scheduled_tasks "
                    "SET last_run_at=?, last_status=?, next_run_at=? "
                    "WHERE job_id=?",
                    (now, status, next_run, event.job_id),
                )
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to update job status in DB: %s", exc)
        if event.exception:
            log.error("Scheduled job %s failed: %s", event.job_id, event.exception)

    def _upsert_db_record(
        self,
        job_id: str,
        task_type: str,
        cron_expr: str | None,
        interval_min: int | None,
    ) -> None:
        job = self._sched.get_job(job_id)
        next_run = job.next_run_time.isoformat() if (job and job.next_run_time) else None
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO scheduled_tasks
                    (job_id, task_type, cron_expr, interval_min, is_enabled,
                     next_run_at, created_at)
                VALUES (?, ?, ?, ?, 1, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(job_id) DO UPDATE SET
                    task_type    = excluded.task_type,
                    cron_expr    = excluded.cron_expr,
                    interval_min = excluded.interval_min,
                    is_enabled   = 1,
                    next_run_at  = excluded.next_run_at
                """,
                (job_id, task_type, cron_expr, interval_min, next_run),
            )

    def _sync_from_db(self) -> None:
        """Re-register enabled jobs from the DB after a restart."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM scheduled_tasks WHERE is_enabled = 1"
            ).fetchall()
        for row in rows:
            try:
                if row["cron_expr"]:
                    self.add_cron_job(row["task_type"], row["cron_expr"], job_id=row["job_id"])
                elif row["interval_min"]:
                    self.add_interval_job(row["task_type"], row["interval_min"], job_id=row["job_id"])
            except Exception as exc:  # noqa: BLE001
                log.warning("Could not restore job %s: %s", row["job_id"], exc)


# Module-level singleton — import and call start() once.
_instance: SchedulerService | None = None


def get_scheduler() -> SchedulerService:
    global _instance  # noqa: PLW0603
    if _instance is None:
        _instance = SchedulerService()
    return _instance
