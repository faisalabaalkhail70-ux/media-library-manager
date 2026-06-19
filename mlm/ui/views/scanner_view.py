from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
    QFileDialog, QLineEdit, QMessageBox, QComboBox, QProgressBar
)
from mlm.app.config import AppConfig
from mlm.db.repositories.directories_repo import DirectoriesRepository
from mlm.workers.scan_worker import ScanWorker

class ScannerView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.config = AppConfig()
        self.directories_repo = DirectoriesRepository()
        self.worker = None
        self.current_directory_id = None

        layout = QVBoxLayout(self)

        title = QLabel("Scanner")
        title.setObjectName("h1")
        layout.addWidget(title)

        row = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select a media root directory...")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_directory)
        row.addWidget(self.path_input)
        row.addWidget(browse_btn)
        layout.addLayout(row)

        row2 = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["mixed", "movie", "tv"])
        self.scan_btn = QPushButton("Add & Scan")
        self.scan_btn.setObjectName("primary")
        self.scan_btn.clicked.connect(self.toggle_scan)
        row2.addWidget(self.type_combo)
        row2.addWidget(self.scan_btn)
        layout.addLayout(row2)

        self.status_label = QLabel("Idle.")
        self.status_label.setObjectName("muted")
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)

        layout.addStretch()

    def browse_directory(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select media root")
        if path:
            self.path_input.setText(path)

    def toggle_scan(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.scan_btn.setText("Add & Scan")
            self.progress.hide()
            self.status_label.setText("Cancelling scan...")
            return

        path = self.path_input.text().strip()
        if not path:
            QMessageBox.warning(self, "Missing folder", "Choose a directory first.")
            return

        library_type = self.type_combo.currentText()
        self.directories_repo.add_directory(path, library_type)
        directories = self.directories_repo.list_directories()
        match = next((d for d in directories if d["path"] == path), None)
        if not match:
            QMessageBox.critical(self, "Error", "Failed to register directory.")
            return

        self.current_directory_id = match["id"]
        self.worker = ScanWorker(
            directory_id=self.current_directory_id,
            root_path=path,
            valid_exts=self.config.supported_video_exts,
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.finished_scan.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)

        self.progress.show()
        self.scan_btn.setText("Stop Scan")
        self.status_label.setText("Scanning...")
        self.worker.start()

    def on_progress(self, count: int, name: str) -> None:
        self.status_label.setText(f"Scanned {count} files... {name}")

    def on_finished(self, result: dict) -> None:
        self.progress.hide()
        self.scan_btn.setText("Add & Scan")
        self.status_label.setText(
            f'{result["status"].capitalize()}: {result["files_seen"]} files processed.'
        )

    def on_failed(self, message: str) -> None:
        self.progress.hide()
        self.scan_btn.setText("Add & Scan")
        self.status_label.setText("Scan failed.")
        QMessageBox.critical(self, "Scan failed", message)