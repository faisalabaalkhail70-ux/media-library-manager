from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QGroupBox, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from mlm.workers.health_worker import HealthWorker
from mlm.db.connection import get_connection


STATUS_COLORS = {
    "ok":      "#81c784",
    "warning": "#fff176",
    "error":   "#ef5350",
}


class HealthView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("File Health Checks")
        title.setObjectName("h1")
        layout.addWidget(title)

        # ── Toolbar ───────────────────────────────────────────────
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

        # ── Progress ──────────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)

        # ── Summary Cards ─────────────────────────────────────────
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

        # ── Results Table ─────────────────────────────────────────
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

    # ── Helpers ───────────────────────────────────────────────────

    def _summary_card(self, label: str, value: str, color: str) -> tuple:
        from PySide6.QtWidgets import QFrame
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

    # ── Data ──────────────────────────────────────────────────────

    def load_rows(self) -> None:
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
                row.get("health_notes", "") or "\u2014",
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
            self.status_label.setText("No health data \u2014 run a scan first.")
        else:
            self.status_label.setText(
                f"{total} files checked \u2014 {counts['ok']} OK, "
                f"{counts['warning']} warnings, {counts['error']} errors"
            )

    # ── Actions ───────────────────────────────────────────────────

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
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Health scan failed", message)
