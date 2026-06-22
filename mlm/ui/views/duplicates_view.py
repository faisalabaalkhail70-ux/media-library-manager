"""Duplicates view — shows exact, quality-variant, and possible duplicate groups.

New in this revision
  - Ignore Group button: permanently dismisses a false-positive group
  - Score breakdown shown in status bar when a row is selected
  - Shows quality-variant count in summary
  - include_ignored toggle to review dismissed groups
"""
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTableView,
    QHBoxLayout, QMessageBox, QProgressBar, QAbstractItemView,
    QCheckBox
)
from PySide6.QtCore import Qt
from mlm.db.repositories.duplicates_repo import DuplicatesRepository
from mlm.ui.models.duplicates_model import DuplicatesModel
from mlm.workers.duplicate_worker import DuplicateWorker


class DuplicatesView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.repo   = DuplicatesRepository()
        self.model  = DuplicatesModel([])
        self.worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Duplicates")
        title.setObjectName("h1")
        layout.addWidget(title)

        # ── Toolbar ───────────────────────────────────────────────
        toolbar = QHBoxLayout()

        self.find_btn = QPushButton("Find Duplicates")
        self.find_btn.setObjectName("primary")
        self.find_btn.clicked.connect(self.find_duplicates)

        self.clear_btn = QPushButton("Clear Results")
        self.clear_btn.clicked.connect(self.clear_results)

        self.ignore_btn = QPushButton("Ignore Group")
        self.ignore_btn.setToolTip(
            "Mark the selected group as a false positive.\n"
            "It will be excluded from future scans."
        )
        self.ignore_btn.clicked.connect(self._ignore_selected_group)

        self.show_ignored_cb = QCheckBox("Show ignored")
        self.show_ignored_cb.stateChanged.connect(self._reload)

        self.status_label = QLabel("No scan performed yet.")
        self.status_label.setObjectName("muted")

        toolbar.addWidget(self.find_btn)
        toolbar.addWidget(self.clear_btn)
        toolbar.addWidget(self.ignore_btn)
        toolbar.addWidget(self.show_ignored_cb)
        toolbar.addStretch()
        toolbar.addWidget(self.status_label)
        layout.addLayout(toolbar)

        # ── Progress ───────────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)

        # ── Table ─────────────────────────────────────────────────
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSortingEnabled(False)
        self.table.selectionModel().selectionChanged.connect(self._on_selection)
        layout.addWidget(self.table)

        # ── Score breakdown bar ───────────────────────────────────────
        self._score_lbl = QLabel("")
        self._score_lbl.setObjectName("muted")
        self._score_lbl.setStyleSheet("font-size: 11px; padding: 2px 0;")
        layout.addWidget(self._score_lbl)

        self.load_rows()

    # ── Data ──────────────────────────────────────────────────

    def load_rows(self) -> None:
        self._reload()

    def _reload(self) -> None:
        include_ignored = self.show_ignored_cb.isChecked()
        rows = self.repo.fetch_duplicate_rows(include_ignored=include_ignored)
        self.model.set_rows(rows)
        self._update_status(rows)
        self._score_lbl.setText("")

    def _update_status(self, rows: list[dict]) -> None:
        if not rows:
            self.status_label.setText("No duplicates found.")
            return
        exact    = sum(1 for r in rows if r["match_type"] == "exact")
        quality  = sum(1 for r in rows if r["match_type"] == "quality")
        possible = sum(1 for r in rows if r["match_type"] == "possible")
        ignored  = sum(1 for r in rows if r["review_status"] == "ignored")
        parts = [f"{len(rows)} files in groups"]
        if exact:    parts.append(f"{exact} exact")
        if quality:  parts.append(f"{quality} quality-variant")
        if possible: parts.append(f"{possible} possible")
        if ignored:  parts.append(f"{ignored} ignored")
        self.status_label.setText("  —  ".join(parts))

    # ── Actions ────────────────────────────────────────────────

    def find_duplicates(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        self.find_btn.setEnabled(False)
        self.progress.show()
        self.status_label.setText("Scanning for duplicates...")
        self.worker = DuplicateWorker()
        self.worker.finished_build.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def clear_results(self) -> None:
        reply = QMessageBox.question(
            self, "Clear Results",
            "Clear ALL duplicate scan results (including ignored groups)?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.repo.clear_groups()
            self.model.set_rows([])
            self.status_label.setText("Results cleared.")
            self._score_lbl.setText("")

    def _ignore_selected_group(self) -> None:
        row = self._current_row()
        if row is None:
            QMessageBox.information(self, "No selection", "Select a row first.")
            return
        group_id = row.get("group_id")
        reply = QMessageBox.question(
            self, "Ignore Group",
            f"Mark group {group_id} as a false positive?\n"
            "It will be hidden and excluded from future scans.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.repo.ignore_group(group_id)
            self._reload()

    def _current_row(self) -> dict | None:
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return None
        return self.model.get_row(sel[0].row())

    def _on_selection(self) -> None:
        row = self._current_row()
        if row is None:
            self._score_lbl.setText("")
            return
        try:
            reason = json.loads(row.get("reason_json") or "{}")
        except Exception:
            reason = {}
        parts = []
        if "name_score" in reason:
            parts.append(f"Name: {reason['name_score']:.2f}")
        if "duration_score" in reason:
            parts.append(f"Duration: {reason['duration_score']:.2f}")
        if "size_score" in reason:
            parts.append(f"Size: {reason['size_score']:.2f}")
        if "reason" in reason:
            parts.append(f"Reason: {reason['reason']}")
        if "resolution" in reason:
            parts.append(f"Resolution: {reason['resolution']}")
        score_text = "  |  ".join(parts) if parts else ""
        overall = row.get("score") or row.get("confidence") or ""
        if overall:
            score_text = f"Overall: {float(overall):.2f}   {score_text}"
        self._score_lbl.setText(score_text)

    def on_finished(self, result: dict) -> None:
        self.progress.hide()
        self.find_btn.setEnabled(True)
        self._reload()
        QMessageBox.information(
            self,
            "Duplicate Scan Complete",
            f'Exact groups: {result["exact_groups"]}\n'
            f'Quality-variant groups: {result.get("quality_groups", 0)}\n'
            f'Possible groups: {result["possible_groups"]}',
        )

    def on_failed(self, message: str) -> None:
        self.progress.hide()
        self.find_btn.setEnabled(True)
        self.status_label.setText("Scan failed.")
        QMessageBox.critical(self, "Duplicate scan failed", message)
