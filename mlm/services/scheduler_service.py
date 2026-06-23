"""E-3 Scheduled Tasks — APScheduler wrapper.

Provides a singleton BackgroundScheduler whose jobs call into existing
service layer functions.  The scheduler runs in a daemon background
thread and never touches the Qt main thread.

Job types (task_type strings)
------------------------------
  'scan_all'        — re-scan every enabled directory
  'health_check'    — run HealthService.run_health_scan()
  'metadata_match'  — match unmatched files via MetadataService
  'snapshot'        — take a library snapshot via SnapshotService
  'health_cards'    — regenerate action cards via HealthScoreService

Usage
-----
    from mlm.services.scheduler_service import get_scheduler
    sched = get_scheduler()
    sched.start_scheduler()
    sched.add_interval_job('health_check', interval_minutes=60)
    sched.add_cron_job('scan_all', cron_expr='0 3 * * *')  # 03:00 daily
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from mlm.db.connection import get_connection

log = logging.getLogger(__name__)

# Lazy imports inside job functions to avoid circular imports at module load
_JOB_REGISTRY: dict[str, Callable] = {}


def _register() -> None:
    """Populate _JOB_REGISTRY once, lazily."""
    if _JOB_REGISTRY:
        return
    from mlm.services.health_service import HealthService
    from mlm.services.health_score_service import HealthScoreService
    from mlm.services.snapshot_service import SnapshotService

    _JOB_REGISTRY["health_check"]   = HealthService().run_health_scan
    _JOB_REGISTRY["health_cards"]   = HealthScoreService().refresh_action_cards
    _JOB_REGISTRY["snapshot"]       = lambda: SnapshotService().take_snapshot(label="auto")

    def _scan_all() -> None:
        from mlm.services.scan_service import ScanService
        from mlm.db.connection import get_connection as gc
        svc = ScanService()
        with gc() as conn:
            dirs = conn.execute(
                "SELECT id, path FROM directories WHERE is_enabled=1"
            ).fetchall()
        for d in dirs:
            try:
                svc.scan_directory(d["id"], d["path"])
            except Exception as exc:  # noqa: BLE001
                log.error("Scheduled scan failed for '%s': %s", d["path"], exc)

    _JOB_REGISTRY["scan_all"] = _scan_all

    def _metadata_match() -> None:
        from mlm.services.metadata_service import MetadataService
        from mlm.db.connection import get_connection as gc
        svc = MetadataService()
        with gc() as conn:
            rows = conn.execute(
                "SELECT id FROM media_files WHERE entity_id IS NULL AND removed_at IS NULL"
            ).fetchall()
        for row in rows:
            try:
                svc.match_file(row["id"])
            except Exception as exc:  # noqa: BLE001
                log.warning("Metadata match failed for file_id=%d: %s", row["id"], exc)

    _JOB_REGISTRY["metadata_match"] = _metadata_match


def _run_job(task_type: str, job_id: str) -> None:
    """Wrapper executed by APScheduler; updates scheduled_tasks table."""
    _register()
    fn = _JOB_REGISTRY.get(task_type)
    if not fn:
        log.error("Unknown task_type '%s' for job '%s'", task_type, job_id)
        return
    now = datetime.utcnow().isoformat()
    try:
        log.info("[Scheduler] Starting job '%s' (type=%s)", job_id, task_type)
        fn()
        status = "ok"
        log.info("[Scheduler] Job '%s' completed.", job_id)
    except Exception as exc:  # noqa: BLE001
        status = f"error: {exc}"
        log.error("[Scheduler] Job '%s' failed: %s", job_id, exc, exc_info=True)
    with get_connection() as conn:
        conn.execute(
            "UPDATE scheduled_tasks SET last_run_at=?, last_status=? WHERE job_id=?",
            (now, status, job_id),
        )


class SchedulerService:
    """Thin wrapper around APScheduler's BackgroundScheduler."""

    def __init__(self) -> None:
        self._sched = BackgroundScheduler(daemon=True)
        self._started = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_scheduler(self) -> None:
        if not self._started:
            self._sched.start()
            self._started = True
            log.info("[Scheduler] Started.")
            self._restore_from_db()

    def shutdown(self) -> None:
        if self._started:
            self._sched.shutdown(wait=False)
            self._started = False
            log.info("[Scheduler] Shut down.")

    # ------------------------------------------------------------------
    # Job management
    # ------------------------------------------------------------------

    def add_interval_job(
        self, task_type: str, interval_minutes: int, job_id: str | None = None
    ) -> str:
        job_id = job_id or f"{task_type}_interval"
        trigger = IntervalTrigger(minutes=interval_minutes)
        self._upsert_job(job_id, task_type, trigger)
        self._persist_job(
            job_id, task_type, interval_min=interval_minutes, cron_expr=None
        )
        return job_id

    def add_cron_job(
        self, task_type: str, cron_expr: str, job_id: str | None = None
    ) -> str:
        """*cron_expr* is a 5-field POSIX cron string e.g. '0 3 * * *'."""
        job_id  = job_id or f"{task_type}_cron"
        parts   = cron_expr.split()
        trigger = CronTrigger(
            minute=parts[0], hour=parts[1],
            day=parts[2],    month=parts[3], day_of_week=parts[4],
        )
        self._upsert_job(job_id, task_type, trigger)
        self._persist_job(
            job_id, task_type, interval_min=None, cron_expr=cron_expr
        )
        return job_id

    def remove_job(self, job_id: str) -> None:
        try:
            self._sched.remove_job(job_id)
        except Exception:  # noqa: BLE001
            pass
        with get_connection() as conn:
            conn.execute(
                "UPDATE scheduled_tasks SET is_enabled=0 WHERE job_id=?", (job_id,)
            )

    def list_jobs(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM scheduled_tasks ORDER BY task_type"
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _upsert_job(self, job_id: str, task_type: str, trigger) -> None:
        if self._sched.get_job(job_id):
            self._sched.remove_job(job_id)
        self._sched.add_job(
            _run_job, trigger,
            args=[task_type, job_id],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=120,
        )

    def _persist_job(
        self,
        job_id: str,
        task_type: str,
        interval_min: int | None,
        cron_expr: str | None,
    ) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO scheduled_tasks (job_id, task_type, cron_expr, interval_min, is_enabled)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(job_id) DO UPDATE SET
                    task_type    = excluded.task_type,
                    cron_expr    = excluded.cron_expr,
                    interval_min = excluded.interval_min,
                    is_enabled   = 1
                """,
                (job_id, task_type, cron_expr, interval_min),
            )

    def _restore_from_db(self) -> None:
        """Re-register any enabled jobs persisted from a previous session."""
        rows = self.list_jobs()
        for r in rows:
            if not r["is_enabled"]:
                continue
            try:
                if r["cron_expr"]:
                    self.add_cron_job(r["task_type"], r["cron_expr"], r["job_id"])
                elif r["interval_min"]:
                    self.add_interval_job(
                        r["task_type"], r["interval_min"], r["job_id"]
                    )
            except Exception as exc:  # noqa: BLE001
                log.warning("Could not restore job '%s': %s", r["job_id"], exc)


# Module-level singleton -------------------------------------------------
_instance: SchedulerService | None = None


def get_scheduler() -> SchedulerService:
    global _instance
    if _instance is None:
        _instance = SchedulerService()
    return _instance
