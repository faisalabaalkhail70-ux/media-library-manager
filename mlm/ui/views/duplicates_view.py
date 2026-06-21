from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTableView,
    QHBoxLayout, QMessageBox, QProgressBar, QAbstractItemView
)
from PySide6.QtCore import Qt
from mlm.db.repositories.duplicates_repo import DuplicatesRepository
from mlm.ui.models.duplicates_model import DuplicatesModel
from mlm.workers.duplicate_worker import DuplicateWorker


class DuplicatesView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.repo = DuplicatesRepository()
        self.model = DuplicatesModel([])
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

        self.status_label = QLabel("No scan performed yet.")
        self.status_label.setObjectName("muted")

        toolbar.addWidget(self.find_btn)
        toolbar.addWidget(self.clear_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.status_label)
        layout.addLayout(toolbar)

        # ── Progress ──────────────────────────────────────────────
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
        layout.addWidget(self.table)

        self.load_rows()

    # ── Data ──────────────────────────────────────────────────────

    def load_rows(self) -> None:
        rows = self.repo.fetch_duplicate_rows()
        self.model.set_rows(rows)
        self._update_status(rows)

    def _update_status(self, rows: list[dict]) -> None:
        if not rows:
            self.status_label.setText("No duplicates found.")
            return
        exact = sum(1 for r in rows if r["match_type"] == "exact")
        possible = sum(1 for r in rows if r["match_type"] == "possible")
        self.status_label.setText(
            f"{len(rows)} files in groups — {exact} exact, {possible} possible"
        )

    # ── Actions ───────────────────────────────────────────────────

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
            "Clear all duplicate scan results from the database?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.repo.clear_groups()
            self.model.set_rows([])
            self.status_label.setText("Results cleared.")

    def on_finished(self, result: dict) -> None:
        self.progress.hide()
        self.find_btn.setEnabled(True)
        self.load_rows()
        QMessageBox.information(
            self,
            "Duplicate Scan Complete",
            f'Exact groups: {result["exact_groups"]}\n'
            f'Possible groups: {result["possible_groups"]}',
        )

    def on_failed(self, message: str) -> None:
        self.progress.hide()
        self.find_btn.setEnabled(True)
        self.status_label.setText("Scan failed.")
        QMessageBox.critical(self, "Duplicate scan failed", message)