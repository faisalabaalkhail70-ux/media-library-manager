from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTableView, QHBoxLayout, QMessageBox
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

        title = QLabel("Duplicates")
        title.setObjectName("h1")
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        self.find_btn = QPushButton("Find Duplicates")
        self.find_btn.clicked.connect(self.find_duplicates)
        toolbar.addWidget(self.find_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.load_rows()

    def load_rows(self) -> None:
        self.model.set_rows(self.repo.fetch_duplicate_rows())

    def find_duplicates(self) -> None:
        self.worker = DuplicateWorker()
        self.worker.finished_build.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def on_finished(self, result: dict) -> None:
        self.load_rows()
        QMessageBox.information(
            self,
            "Duplicate scan complete",
            f'Exact groups: {result["exact_groups"]}\nPossible groups: {result["possible_groups"]}'
        )

    def on_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Duplicate scan failed", message)