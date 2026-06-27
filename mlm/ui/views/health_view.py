"""Health view — includes CorruptedFoldersPanel and per-task action buttons
with live progress for: Check Missing Episodes, Auto Match Metadata, Run ffprobe Enrich."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QGroupBox, QAbstractItemView, QFrame, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from mlm.workers.health_worker   import HealthWorker
from mlm.workers.episode_worker  import EpisodeWorker
from mlm.workers.metadata_worker import MetadataWorker
from mlm.workers.probe_worker    import ProbeWorker
from mlm.db.connection import get_connection
from mlm.ui.corrupted_folders_panel import CorruptedFoldersPanel
from mlm.ui.widgets import SectionHeader


STATUS_COLORS = {
    "ok":      "#81c784",
    "warning": "#fff176",
    "error":   "#ef5350",
}


class HealthView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.worker          = None   # HealthWorker
        self._ep_worker      = None   # EpisodeWorker
        self._meta_worker    = None   # MetadataWorker
        self._probe_worker   = None   # ProbeWorker

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ── Page title
        title = QLabel("File Health Checks")
        title.setObjectName("h1")
        layout.addWidget(title)

        # ── Main toolbar (existing health scan)
        toolbar = QHBoxLayout()
        self.scan_btn = QPushButton("Run Health Scan")
        self.scan_btn.setObjectName("primary")
        self.scan_btn.clicked.connect(self.run_scan)
        self.refresh_btn = QPushButton("Refresh Results")
        self.refresh_btn.clicked.connect(self.load_rows)
        self.status_label = QLabel("No scan performed yet.")
        self.status_label.setObjectName("muted")
        toolbar.addWidget(self.scan_btn)
        toolbar.addWidget(self.refresh_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.status_label)
        layout.addLayout(toolbar)

        # ── Progress bar (health scan)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)

        # ── Summary cards
        summary_row = QHBoxLayout()
        summary_row.setSpacing(12)
        self.ok_card    = self._summary_card("OK",       "0", "#81c784")
        self.warn_card  = self._summary_card("Warnings", "0", "#fff176")
        self.error_card = self._summary_card("Errors",   "0", "#ef5350")
        summary_row.addWidget(self.ok_card[0])
        summary_row.addWidget(self.warn_card[0])
        summary_row.addWidget(self.error_card[0])
        summary_row.addStretch()
        layout.addLayout(summary_row)

        # ── Maintenance tasks group box
        tasks_group = QGroupBox("Maintenance Tasks")
        tasks_lay = QVBoxLayout(tasks_group)
        tasks_lay.setSpacing(10)

        # --- Check Missing Episodes
        ep_row = QHBoxLayout()
        self._ep_btn = QPushButton("Check Missing Episodes")
        self._ep_btn.setFixedWidth(220)
        self._ep_btn.clicked.connect(self._run_episode_check)
        self._ep_progress = QProgressBar()
        self._ep_progress.setRange(0, 0)
        self._ep_progress.setFixedHeight(6)
        self._ep_progress.hide()
        self._ep_label = QLabel("")
        self._ep_label.setObjectName("muted")
        ep_row.addWidget(self._ep_btn)
        ep_row.addWidget(self._ep_progress, 1)
        ep_row.addWidget(self._ep_label)
        tasks_lay.addLayout(ep_row)

        # --- Auto Match Metadata
        meta_row = QHBoxLayout()
        self._meta_btn = QPushButton("Auto Match Metadata")
        self._meta_btn.setFixedWidth(220)
        self._meta_btn.clicked.connect(self._run_metadata_match)
        self._meta_progress = QProgressBar()
        self._meta_progress.setRange(0, 0)
        self._meta_progress.setFixedHeight(6)
        self._meta_progress.hide()
        self._meta_label = QLabel("")
        self._meta_label.setObjectName("muted")
        meta_row.addWidget(self._meta_btn)
        meta_row.addWidget(self._meta_progress, 1)
        meta_row.addWidget(self._meta_label)
        tasks_lay.addLayout(meta_row)

        # --- Run ffprobe Enrich
        probe_row = QHBoxLayout()
        self._probe_btn = QPushButton("Run ffprobe Enrich")
        self._probe_btn.setFixedWidth(220)
        self._probe_btn.clicked.connect(self._run_probe_enrich)
        self._probe_progress = QProgressBar()
        self._probe_progress.setRange(0, 0)
        self._probe_progress.setFixedHeight(6)
        self._probe_progress.hide()
        self._probe_label = QLabel("")
        self._probe_label.setObjectName("muted")
        probe_row.addWidget(self._probe_btn)
        probe_row.addWidget(self._probe_progress, 1)
        probe_row.addWidget(self._probe_label)
        tasks_lay.addLayout(probe_row)

        layout.addWidget(tasks_group)

        # ── Corrupted Folders Panel
        self.corrupted_panel = CorruptedFoldersPanel()
        layout.addWidget(self.corrupted_panel)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: rgba(255,255,255,8);")
        layout.addWidget(sep)

        # ── File-level results table
        layout.addWidget(SectionHeader(
            "All Scanned Files",
            "Every file that has been health-checked, sorted by severity",
            QColor(120, 144, 156),
        ))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Status", "Filename", "Notes", "Path"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        self.load_rows()

    # ── Helpers ───────────────────────────────────────────────────────
    def _summary_card(self, label: str, value: str, color: str) -> tuple:
        card = QFrame()
        card.setObjectName("stat_card")
        card.setFixedSize(130, 70)
        inner = QVBoxLayout(card)
        inner.setContentsMargins(12, 8, 12, 8)
        val_lbl = QLabel(value)
        val_lbl.setAlignment(Qt.AlignCenter)
        val_lbl.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {color}; background: transparent;"
        )
        lbl = QLabel(label)
        lbl.setObjectName("muted")
        lbl.setAlignment(Qt.AlignCenter)
        inner.addWidget(val_lbl)
        inner.addWidget(lbl)
        return card, val_lbl

    def _update_summary(self, counts: dict) -> None:
        self.ok_card[1].setText(str(counts.get("ok", 0)))
        self.warn_card[1].setText(str(counts.get("warning", 0)))
        self.error_card[1].setText(str(counts.get("error", 0)))

    # ── Data ─────────────────────────────────────────────────────────
    def load_rows(self) -> None:
        self.corrupted_panel.reload()

        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT file_name, file_path, health_status, health_notes
                FROM media_files
                WHERE removed_at IS NULL
                  AND health_status IS NOT NULL
                ORDER BY
                    CASE health_status
                        WHEN 'error'   THEN 1
                        WHEN 'warning' THEN 2
                        ELSE 3
                    END,
                    file_name
                """
            ).fetchall()

        rows = [dict(r) for r in rows]
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        counts = {"ok": 0, "warning": 0, "error": 0}

        for row in rows:
            status = row.get("health_status") or "ok"
            counts[status] = counts.get(status, 0) + 1
            color = QColor(STATUS_COLORS.get(status, "#e0e0e0"))
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            cells = [
                status.upper(),
                row.get("file_name", ""),
                row.get("health_notes", "") or "—",
                row.get("file_path", ""),
            ]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setForeground(color if col == 0 else QColor("#e0e0e0"))
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table.setItem(row_idx, col, item)

        self.table.setSortingEnabled(True)
        self._update_summary(counts)

        total = len(rows)
        if total == 0:
            self.status_label.setText("No health data — run a scan first.")
        else:
            self.status_label.setText(
                f"{total} files checked — {counts['ok']} OK, "
                f"{counts['warning']} warnings, {counts['error']} errors"
            )

    # ── Health scan (existing) ────────────────────────────────────────
    def run_scan(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        self.scan_btn.setEnabled(False)
        self.progress.show()
        self.status_label.setText("Running health scan...")
        self.worker = HealthWorker()
        self.worker.finished_scan.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def on_finished(self, counts: dict) -> None:
        self.progress.hide()
        self.scan_btn.setEnabled(True)
        self.load_rows()

    def on_failed(self, message: str) -> None:
        self.progress.hide()
        self.scan_btn.setEnabled(True)
        self.status_label.setText("Scan failed.")
        QMessageBox.critical(self, "Health scan failed", message)

    # ── Check Missing Episodes ────────────────────────────────────────
    def _run_episode_check(self) -> None:
        if self._ep_worker and self._ep_worker.isRunning():
            return
        self._ep_btn.setEnabled(False)
        self._ep_progress.setRange(0, 0)
        self._ep_progress.show()
        self._ep_label.setText("Checking...")
        self._ep_worker = EpisodeWorker()
        self._ep_worker.finished_check.connect(self._on_episode_done)
        self._ep_worker.failed.connect(lambda msg: self._on_task_failed("Episode check", msg, self._ep_btn, self._ep_progress, self._ep_label))
        self._ep_worker.start()

    def _on_episode_done(self, result: list) -> None:
        self._ep_progress.hide()
        self._ep_btn.setEnabled(True)
        missing = sum(r.get("missing_count", 0) for r in result) if result else 0
        self._ep_label.setText(f"Done — {missing} missing episode(s) found")
        self.load_rows()

    # ── Auto Match Metadata ───────────────────────────────────────────
    def _run_metadata_match(self) -> None:
        if self._meta_worker and self._meta_worker.isRunning():
            return
        self._meta_btn.setEnabled(False)
        self._meta_progress.setRange(0, 0)
        self._meta_progress.show()
        self._meta_label.setText("Matching...")
        self._meta_worker = MetadataWorker()
        self._meta_worker.progress.connect(self._on_meta_progress)
        self._meta_worker.finished_batch.connect(self._on_meta_done)
        self._meta_worker.failed.connect(lambda msg: self._on_task_failed("Metadata match", msg, self._meta_btn, self._meta_progress, self._meta_label))
        self._meta_worker.start()

    def _on_meta_progress(self, current: int, total: int, label: str) -> None:
        self._meta_progress.setRange(0, total)
        self._meta_progress.setValue(current)
        # Truncate long filenames for display
        short = label if len(label) <= 40 else label[:37] + "..."
        self._meta_label.setText(f"{current}/{total}  {short}")

    def _on_meta_done(self) -> None:
        self._meta_progress.hide()
        self._meta_btn.setEnabled(True)
        self._meta_label.setText("Done")
        self.load_rows()

    # ── Run ffprobe Enrich ────────────────────────────────────────────
    def _run_probe_enrich(self) -> None:
        if self._probe_worker and self._probe_worker.isRunning():
            return
        self._probe_btn.setEnabled(False)
        self._probe_progress.setRange(0, 0)
        self._probe_progress.show()
        self._probe_label.setText("Probing...")
        self._probe_worker = ProbeWorker()
        self._probe_worker.progress.connect(self._on_probe_progress)
        self._probe_worker.finished_batch.connect(self._on_probe_done)
        self._probe_worker.failed.connect(lambda msg: self._on_task_failed("ffprobe enrich", msg, self._probe_btn, self._probe_progress, self._probe_label))
        self._probe_worker.start()

    def _on_probe_progress(self, current: int, total: int, path: str) -> None:
        self._probe_progress.setRange(0, total)
        self._probe_progress.setValue(current)
        import os
        short = os.path.basename(path)
        if len(short) > 40:
            short = short[:37] + "..."
        self._probe_label.setText(f"{current}/{total}  {short}")

    def _on_probe_done(self) -> None:
        self._probe_progress.hide()
        self._probe_btn.setEnabled(True)
        self._probe_label.setText("Done")
        self.load_rows()

    # ── Shared error handler ──────────────────────────────────────────
    def _on_task_failed(self, task: str, message: str, btn, prog, lbl) -> None:
        prog.hide()
        btn.setEnabled(True)
        lbl.setText("Failed")
        QMessageBox.critical(self, f"{task} failed", message)
