"""E-3 — Scheduled Tasks UI view.

Shows a table of all APScheduler jobs with:
  • Task type, schedule expression, last run, last status, next run
  • Enable / Disable toggle per row
  • Run Now button
  • Add Task dialog (interval or cron)
  • Remove job button

The view auto-refreshes every 30 s via a QTimer so "Next run" counts
down without any manual user action.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QComboBox, QLineEdit, QRadioButton, QButtonGroup,
    QMessageBox, QSpinBox, QFrame,
)

from mlm.services.scheduler_service import get_scheduler

log = logging.getLogger(__name__)

_TASK_TYPES = ["scan", "health", "snapshot", "restructure"]
_COLS = ["Job ID", "Type", "Schedule", "Last Run", "Status", "Next Run", "Actions"]


class _AddTaskDialog(QDialog):
    """Dialog to create a new scheduled task."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Scheduled Task")
        self.setMinimumWidth(420)
        self.setModal(True)

        lay = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self._type_combo = QComboBox()
        self._type_combo.addItems(_TASK_TYPES)
        form.addRow("Task type:", self._type_combo)

        mode_row = QHBoxLayout()
        self._rb_interval = QRadioButton("Every N minutes")
        self._rb_cron = QRadioButton("Cron expression")
        self._rb_interval.setChecked(True)
        bg = QButtonGroup(self)
        bg.addButton(self._rb_interval)
        bg.addButton(self._rb_cron)
        mode_row.addWidget(self._rb_interval)
        mode_row.addWidget(self._rb_cron)
        form.addRow("Mode:", mode_row)

        self._spin_interval = QSpinBox()
        self._spin_interval.setRange(1, 10080)   # 1 min – 1 week
        self._spin_interval.setValue(60)
        self._spin_interval.setSuffix(" minutes")
        form.addRow("Interval:", self._spin_interval)

        self._cron_edit = QLineEdit()
        self._cron_edit.setPlaceholderText("e.g.  0 3 * * *  (daily at 03:00)")
        self._cron_edit.setEnabled(False)
        form.addRow("Cron:", self._cron_edit)

        self._rb_interval.toggled.connect(self._on_mode_change)

        lay.addLayout(form)

        btns = QHBoxLayout()
        self._btn_ok = QPushButton("Add")
        self._btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(btn_cancel)
        btns.addWidget(self._btn_ok)
        lay.addLayout(btns)

    def _on_mode_change(self, interval_selected: bool) -> None:
        self._spin_interval.setEnabled(interval_selected)
        self._cron_edit.setEnabled(not interval_selected)

    def result_data(self) -> dict:
        return {
            "task_type":   self._type_combo.currentText(),
            "mode":        "interval" if self._rb_interval.isChecked() else "cron",
            "interval":    self._spin_interval.value(),
            "cron_expr":   self._cron_edit.text().strip(),
        }


class SchedulerView(QWidget):
    """Full-page view for managing scheduled tasks."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("Scheduled Tasks")
        title.setStyleSheet("font-size:18px; font-weight:700; color:#c8c4f0;")
        hdr.addWidget(title)
        hdr.addStretch()
        self._btn_add = QPushButton("+ Add Task")
        self._btn_add.setFixedHeight(32)
        self._btn_add.clicked.connect(self._add_task)
        self._btn_refresh = QPushButton("↻ Refresh")
        self._btn_refresh.setFixedHeight(32)
        self._btn_refresh.clicked.connect(self.load_rows)
        hdr.addWidget(self._btn_add)
        hdr.addWidget(self._btn_refresh)
        lay.addLayout(hdr)

        # Info bar
        info = QLabel(
            "Tasks run in background threads and never block the UI. "
            "All times are UTC."
        )
        info.setStyleSheet("color:#6060a0; font-size:11px;")
        lay.addWidget(info)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        lay.addWidget(sep)

        # Table
        self._table = QTableWidget(0, len(_COLS))
        self._table.setHorizontalHeaderLabels(_COLS)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self._table.setColumnWidth(6, 200)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        lay.addWidget(self._table, 1)

        # Auto-refresh timer
        self._timer = QTimer(self)
        self._timer.setInterval(30_000)   # 30 s
        self._timer.timeout.connect(self.load_rows)
        self._timer.start()

        self.load_rows()

    # ------------------------------------------------------------------

    def load_rows(self) -> None:
        try:
            jobs = get_scheduler().list_jobs()
        except Exception as exc:  # noqa: BLE001
            log.warning("SchedulerView: could not list jobs: %s", exc)
            jobs = []

        self._table.setRowCount(0)
        for row_idx, job in enumerate(jobs):
            self._table.insertRow(row_idx)

            schedule = job["cron_expr"] or (
                f"every {job['interval_min']} min" if job["interval_min"] else "—"
            )
            last_run = self._fmt_dt(job["last_run_at"])
            next_run = self._fmt_dt(job["next_run_at"])
            status_text = job["last_status"] or "pending"

            for col, val in enumerate([
                job["job_id"], job["task_type"], schedule,
                last_run, status_text, next_run,
            ]):
                item = QTableWidgetItem(str(val))
                if col == 4:  # status colouring
                    if val == "ok":
                        item.setForeground(Qt.green)
                    elif val == "error":
                        item.setForeground(Qt.red)
                self._table.setItem(row_idx, col, item)

            # Actions cell
            cell = QWidget()
            cell_lay = QHBoxLayout(cell)
            cell_lay.setContentsMargins(4, 2, 4, 2)
            cell_lay.setSpacing(4)

            job_id = job["job_id"]
            is_enabled = bool(job["is_enabled"])

            btn_toggle = QPushButton("Disable" if is_enabled else "Enable")
            btn_toggle.setFixedHeight(24)
            btn_toggle.clicked.connect(lambda _, jid=job_id, en=is_enabled: self._toggle(jid, en))

            btn_now = QPushButton("▶ Now")
            btn_now.setFixedHeight(24)
            btn_now.clicked.connect(lambda _, jid=job_id: self._run_now(jid))

            btn_del = QPushButton("✕")
            btn_del.setFixedHeight(24)
            btn_del.setFixedWidth(28)
            btn_del.clicked.connect(lambda _, jid=job_id: self._remove(jid))

            cell_lay.addWidget(btn_toggle)
            cell_lay.addWidget(btn_now)
            cell_lay.addWidget(btn_del)
            self._table.setCellWidget(row_idx, 6, cell)

    # ------------------------------------------------------------------

    def _add_task(self) -> None:
        dlg = _AddTaskDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        data = dlg.result_data()
        try:
            sched = get_scheduler()
            if data["mode"] == "interval":
                sched.add_interval_job(data["task_type"], data["interval"])
            else:
                if not data["cron_expr"]:
                    QMessageBox.warning(self, "Validation", "Cron expression cannot be empty.")
                    return
                sched.add_cron_job(data["task_type"], data["cron_expr"])
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
            return
        self.load_rows()

    def _toggle(self, job_id: str, currently_enabled: bool) -> None:
        sched = get_scheduler()
        try:
            if currently_enabled:
                sched.disable_job(job_id)
            else:
                sched.enable_job(job_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
        self.load_rows()

    def _run_now(self, job_id: str) -> None:
        try:
            get_scheduler().run_now(job_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))

    def _remove(self, job_id: str) -> None:
        ans = QMessageBox.question(
            self, "Remove Task",
            f"Remove scheduled task '{job_id}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ans == QMessageBox.Yes:
            get_scheduler().remove_job(job_id)
            self.load_rows()

    @staticmethod
    def _fmt_dt(iso: str | None) -> str:
        if not iso:
            return "—"
        try:
            dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            local = dt.astimezone()
            return local.strftime("%Y-%m-%d  %H:%M")
        except Exception:  # noqa: BLE001
            return iso
