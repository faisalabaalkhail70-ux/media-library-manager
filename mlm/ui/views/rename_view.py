from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
    QLineEdit, QTableView, QMessageBox, QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt
from mlm.services.rename_service import RenameService
from mlm.services.undo_service import UndoService
from mlm.db.repositories.settings_repo import SettingsRepository
from mlm.ui.models.rename_preview_model import RenamePreviewModel
from mlm.workers.rename_worker import RenameWorker


class RenameView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.rename_service = RenameService()
        self.undo_service = UndoService()
        self.settings = SettingsRepository()
        self.model = RenamePreviewModel([])
        self.worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Smart Rename")
        title.setObjectName("h1")
        layout.addWidget(title)

        # ── Template Group ────────────────────────────────────────
        tmpl_group = QGroupBox("Rename Template")
        tmpl_layout = QVBoxLayout(tmpl_group)

        hint = QLabel(
            "Available tokens:  "
            "<b>{Title}</b>  {Year}  {Season:02}  {Episode:02}  {Resolution}  {Ext}<br>"
            "Examples:<br>"
            "  Movie:   <code>{Title} ({Year}){Ext}</code><br>"
            "  TV Show: <code>{Title} - S{Season:02}E{Episode:02}{Ext}</code>"
        )
        hint.setObjectName("muted")
        hint.setTextFormat(Qt.RichText)
        hint.setWordWrap(True)
        tmpl_layout.addWidget(hint)

        row = QHBoxLayout()
        self.template_input = QLineEdit()
        self.template_input.setPlaceholderText("{Title} ({Year}){Ext}")
        self._load_template()

        self.preview_btn = QPushButton("Preview")
        self.preview_btn.setObjectName("primary")
        self.preview_btn.clicked.connect(self.preview)

        self.clear_btn = QPushButton("Clear Preview")
        self.clear_btn.clicked.connect(self.clear_preview)

        row.addWidget(self.template_input, 1)
        row.addWidget(self.preview_btn)
        row.addWidget(self.clear_btn)
        tmpl_layout.addLayout(row)

        layout.addWidget(tmpl_group)

        # ── Action Buttons ────────────────────────────────────────
        actions = QHBoxLayout()
        self.apply_btn = QPushButton("Apply Rename")
        self.apply_btn.clicked.connect(self.apply_changes)

        self.undo_btn = QPushButton("Undo Latest (20)")
        self.undo_btn.clicked.connect(self.undo_latest)

        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")

        actions.addWidget(self.apply_btn)
        actions.addWidget(self.undo_btn)
        actions.addStretch()
        actions.addWidget(self.status_label)
        layout.addLayout(actions)

        # ── Preview Table ─────────────────────────────────────────
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(False)
        layout.addWidget(self.table)

    # ── Helpers ───────────────────────────────────────────────────

    def _load_template(self) -> None:
        saved = self.settings.get("rename_template", "{Title} ({Year}){Ext}")
        self.template_input.setText(saved)

    def _update_status(self) -> None:
        rows = self.model.rows()
        if not rows:
            self.status_label.setText("")
            return
        valid = sum(1 for r in rows if r["status"] == "valid")
        conflict = sum(1 for r in rows if r["status"] == "conflict")
        unchanged = sum(1 for r in rows if r["status"] == "unchanged")
        self.status_label.setText(
            f"{len(rows)} files — {valid} valid  {conflict} conflicts  {unchanged} unchanged"
        )

    # ── Actions ───────────────────────────────────────────────────

    def preview(self) -> None:
        template = self.template_input.text().strip()
        if not template:
            QMessageBox.warning(self, "Empty template", "Enter a rename template first.")
            return
        rows = self.rename_service.build_preview(template)
        self.model.set_rows(rows)
        self._update_status()

    def clear_preview(self) -> None:
        self.model.set_rows([])
        self.status_label.setText("")

    def apply_changes(self) -> None:
        rows = [r for r in self.model.rows() if r["status"] == "valid"]
        if not rows:
            QMessageBox.information(self, "Nothing to apply", "No valid rename operations.")
            return
        reply = QMessageBox.question(
            self, "Apply Rename",
            f"Rename {len(rows)} files? This cannot be undone except via the Undo button.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.apply_btn.setEnabled(False)
        self.worker = RenameWorker(rows)
        self.worker.finished_apply.connect(self.on_applied)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def on_applied(self, result: dict) -> None:
        self.apply_btn.setEnabled(True)
        QMessageBox.information(
            self, "Rename Complete",
            f'Success: {result["success"]}  Failed: {result["failed"]}',
        )
        self.preview()

    def on_failed(self, message: str) -> None:
        self.apply_btn.setEnabled(True)
        QMessageBox.critical(self, "Rename failed", message)

    def undo_latest(self) -> None:
        reply = QMessageBox.question(
            self, "Undo Renames",
            "Undo the last 20 rename operations?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        result = self.undo_service.undo_latest_renames(limit=20)
        QMessageBox.information(
            self, "Undo Complete",
            f'Undone: {result["undone"]}  Failed: {result["failed"]}',
        )
        self.preview()