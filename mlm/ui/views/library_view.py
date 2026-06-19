from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTableView, QHBoxLayout
from PySide6.QtCore import Qt
from mlm.db.repositories.files_repo import FilesRepository
from mlm.ui.models.media_files_model import MediaFilesTableModel

class LibraryView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.repo = FilesRepository()
        self.model = MediaFilesTableModel([])

        layout = QVBoxLayout(self)

        title = QLabel("Library")
        title.setObjectName("h1")
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_rows)
        toolbar.addWidget(self.refresh_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSortingEnabled(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.load_rows()

    def load_rows(self) -> None:
        rows = self.repo.fetch_library_rows()
        self.model.set_rows(rows)