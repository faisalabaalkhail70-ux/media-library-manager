from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QLineEdit, QTableView, QMessageBox
from mlm.services.rename_service import RenameService
from mlm.services.undo_service import UndoService
from mlm.ui.models.rename_preview_model import RenamePreviewModel
from mlm.workers.rename_worker import RenameWorker

class RenameView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.rename_service = RenameService()
        self.undo_service = UndoService()
        self.model = RenamePreviewModel([])
        self.worker = None

        layout = QVBoxLayout(self)

        title = QLabel("Smart Rename")
        title.setObjectName("h1")
        layout.addWidget(title)

        controls = QHBoxLayout()
        self.template_input = QLineEdit("{Title} ({Year}){Ext}")
        self.preview_btn = QPushButton("Preview")
        self.preview_btn.clicked.connect(self.preview)
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.apply_changes)
        self.undo_btn = QPushButton("Undo Latest")
        self.undo_btn.clicked.connect(self.undo_latest)

        controls.addWidget(self.template_input)
        controls.addWidget(self.preview_btn)
        controls.addWidget(self.apply_btn)
        controls.addWidget(self.undo_btn)
        layout.addLayout(controls)

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

    def preview(self) -> None:
        rows = self.rename_service.build_preview(self.template_input.text().strip())
        self.model.set_rows(rows)

    def apply_changes(self) -> None:
        rows = [r for r in self.model.rows() if r["status"] == "valid"]
        if not rows:
            QMessageBox.information(self, "Nothing to apply", "No valid rename operations.")
            return

        self.worker = RenameWorker(rows)
        self.worker.finished_apply.connect(self.on_applied)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def on_applied(self, result: dict) -> None:
        QMessageBox.information(
            self,
            "Rename complete",
            f'Success: {result["success"]}, Failed: {result["failed"]}'
        )
        self.preview()

    def on_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Rename failed", message)

    def undo_latest(self) -> None:
        result = self.undo_service.undo_latest_renames(limit=20)
        QMessageBox.information(
            self,
            "Undo complete",
            f'Undone: {result["undone"]}, Failed: {result["failed"]}'
        )
        self.preview()