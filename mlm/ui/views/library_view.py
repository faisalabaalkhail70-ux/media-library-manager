from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from mlm.db.repositories.files_repo import FilesRepository
from mlm.services.health_service import HealthService
from mlm.ui.models.media_files_model import MediaFilesTableModel
from mlm.workers.metadata_worker import MetadataWorker
from mlm.workers.probe_worker import ProbeWorker


class LibraryView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.repo = FilesRepository()
        self.health_service = HealthService()
        self.model = MediaFilesTableModel([])
        self.metadata_worker = None
        self.probe_worker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        header = QHBoxLayout()
        title_wrap = QVBoxLayout()
        title_wrap.setSpacing(2)

        title = QLabel("Library")
        title.setObjectName("h1")

        subtitle = QLabel("Browse indexed files and run metadata, probe, and health actions.")
        subtitle.setObjectName("muted")

        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)

        self.refresh_btn = QPushButton("Refresh Library")
        self.refresh_btn.clicked.connect(self.load_rows)

        header.addLayout(title_wrap)
        header.addStretch()
        header.addWidget(self.refresh_btn)

        root.addLayout(header)

        ops_panel = QFrame()
        ops_panel.setObjectName("card")
        ops_layout = QVBoxLayout(ops_panel)
        ops_layout.setContentsMargins(16, 16, 16, 16)
        ops_layout.setSpacing(10)

        ops_title = QLabel("Library Actions")
        ops_title.setObjectName("h1")

        ops_subtitle = QLabel("Run metadata matching, ffprobe enrichment, and health verification.")
        ops_subtitle.setObjectName("muted")

        ops_layout.addWidget(ops_title)
        ops_layout.addWidget(ops_subtitle)

        ops_row = QHBoxLayout()

        self.match_btn = QPushButton("Auto Match Metadata")
        self.match_btn.clicked.connect(self.run_metadata_match)

        self.probe_btn = QPushButton("Run ffprobe Enrich")
        self.probe_btn.clicked.connect(self.run_probe)

        self.health_btn = QPushButton("Run Health Scan")
        self.health_btn.clicked.connect(self.run_health_scan)

        ops_row.addWidget(self.match_btn)
        ops_row.addWidget(self.probe_btn)
        ops_row.addWidget(self.health_btn)
        ops_row.addStretch()

        ops_layout.addLayout(ops_row)

        self.status_label = QLabel("Idle.")
        self.status_label.setObjectName("muted")
        ops_layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.hide()
        ops_layout.addWidget(self.progress)

        root.addWidget(ops_panel)

        summary_panel = QFrame()
        summary_panel.setObjectName("card")
        summary_layout = QHBoxLayout(summary_panel)
        summary_layout.setContentsMargins(16, 14, 16, 14)

        self.count_label = QLabel("0 rows loaded")
        self.count_label.setObjectName("muted")

        summary_layout.addWidget(self.count_label)
        summary_layout.addStretch()

        root.addWidget(summary_panel)

        table_panel = QFrame()
        table_panel.setObjectName("card")
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(12, 12, 12, 12)

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSortingEnabled(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)

        table_layout.addWidget(self.table)
        root.addWidget(table_panel, 1)

        self.load_rows()

    def load_rows(self) -> None:
        rows = self.repo.fetch_library_rows()
        self.model.set_rows(rows)
        self.count_label.setText(f"{len(rows)} rows loaded")

    def run_metadata_match(self) -> None:
        if self.metadata_worker and self.metadata_worker.isRunning():
            self.metadata_worker.stop()
            self.status_label.setText("Stopping metadata match...")
            return

        self.metadata_worker = MetadataWorker(limit=300)
        self.metadata_worker.progress.connect(self.on_metadata_progress)
        self.metadata_worker.finished_batch.connect(self.on_metadata_finished)
        self.metadata_worker.failed.connect(self.on_worker_failed)

        self.progress.show()
        self.progress.setValue(0)
        self.status_label.setText("Matching metadata...")
        self.metadata_worker.start()

    def run_probe(self) -> None:
        if self.probe_worker and self.probe_worker.isRunning():
            self.probe_worker.stop()
            self.status_label.setText("Stopping ffprobe enrich...")
            return

        self.probe_worker = ProbeWorker(limit=300)
        self.probe_worker.progress.connect(self.on_probe_progress)
        self.probe_worker.finished_batch.connect(self.on_probe_finished)
        self.probe_worker.failed.connect(self.on_worker_failed)

        self.progress.show()
        self.progress.setValue(0)
        self.status_label.setText("Running ffprobe enrich...")
        self.probe_worker.start()

    def run_health_scan(self) -> None:
        try:
            result = self.health_service.run_health_scan()
            self.status_label.setText(
                f'Health scan complete. OK: {result["ok"]}, Warning: {result["warning"]}, Error: {result["error"]}'
            )
            QMessageBox.information(
                self,
                "Health Scan Complete",
                f'OK: {result["ok"]}\nWarning: {result["warning"]}\nError: {result["error"]}'
            )
            self.load_rows()
        except Exception as exc:
            self.on_worker_failed(str(exc))

    def on_metadata_progress(self, current: int, total: int, label: str) -> None:
        percent = int((current / total) * 100) if total else 0
        self.progress.setValue(percent)
        self.status_label.setText(f"Metadata {current}/{total}: {label}")

    def on_probe_progress(self, current: int, total: int, label: str) -> None:
        percent = int((current / total) * 100) if total else 0
        self.progress.setValue(percent)
        self.status_label.setText(f"ffprobe {current}/{total}: {label}")

    def on_metadata_finished(self) -> None:
        self.progress.hide()
        self.status_label.setText("Metadata matching complete.")
        self.load_rows()

    def on_probe_finished(self) -> None:
        self.progress.hide()
        self.status_label.setText("ffprobe enrich complete.")
        self.load_rows()

    def on_worker_failed(self, message: str) -> None:
        self.progress.hide()
        self.status_label.setText("Operation failed.")
        QMessageBox.critical(self, "Operation failed", message)