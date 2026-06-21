from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
    QFileDialog, QLineEdit, QMessageBox, QComboBox, QProgressBar,
    QListWidget, QListWidgetItem, QGroupBox
)
from PySide6.QtCore import Qt
from mlm.app.config import AppConfig
from mlm.db.repositories.directories_repo import DirectoriesRepository
from mlm.workers.scan_worker import ScanWorker, DEFAULT_EXCLUDED_FOLDERS


class ScannerView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.config = AppConfig()
        self.directories_repo = DirectoriesRepository()
        self.worker = None
        self.current_directory_id = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Scanner")
        title.setObjectName("h1")
        layout.addWidget(title)

        # ── Add Directory ─────────────────────────────────────────
        add_group = QGroupBox("Add Directory")
        add_layout = QVBoxLayout(add_group)

        row = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select a media root directory...")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_directory)
        row.addWidget(self.path_input)
        row.addWidget(browse_btn)
        add_layout.addLayout(row)

        row2 = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["mixed", "movie", "tv"])
        self.scan_btn = QPushButton("Add & Scan")
        self.scan_btn.setObjectName("primary")
        self.scan_btn.clicked.connect(self.toggle_scan)
        row2.addWidget(QLabel("Type:"))
        row2.addWidget(self.type_combo)
        row2.addStretch()
        row2.addWidget(self.scan_btn)
        add_layout.addLayout(row2)

        layout.addWidget(add_group)

        # ── Registered Directories ────────────────────────────────
        dirs_group = QGroupBox("Registered Directories")
        dirs_layout = QVBoxLayout(dirs_group)

        self.dirs_list = QListWidget()
        self.dirs_list.setFixedHeight(130)
        dirs_layout.addWidget(self.dirs_list)

        dirs_btns = QHBoxLayout()
        self.rescan_btn = QPushButton("Rescan Selected")
        self.rescan_btn.clicked.connect(self.rescan_selected)
        self.remove_dir_btn = QPushButton("Remove Selected")
        self.remove_dir_btn.clicked.connect(self.remove_selected_directory)
        dirs_btns.addWidget(self.rescan_btn)
        dirs_btns.addWidget(self.remove_dir_btn)
        dirs_btns.addStretch()
        dirs_layout.addLayout(dirs_btns)

        layout.addWidget(dirs_group)

        # ── Scan Exclusions ───────────────────────────────────────
        excl_group = QGroupBox("Excluded Folder Names")
        excl_layout = QVBoxLayout(excl_group)

        excl_note = QLabel(
            "Folders with these names will be skipped during scan (case-insensitive, one per line):"
        )
        excl_note.setObjectName("muted")
        excl_note.setWordWrap(True)
        excl_layout.addWidget(excl_note)

        from PySide6.QtWidgets import QPlainTextEdit
        self.excl_edit = QPlainTextEdit()
        self.excl_edit.setFixedHeight(100)
        self.excl_edit.setPlainText(
            "\n".join(sorted(DEFAULT_EXCLUDED_FOLDERS))
        )
        excl_layout.addWidget(self.excl_edit)

        excl_btns = QHBoxLayout()
        reset_excl_btn = QPushButton("Reset to Defaults")
        reset_excl_btn.clicked.connect(self._reset_exclusions)
        excl_btns.addWidget(reset_excl_btn)
        excl_btns.addStretch()
        excl_layout.addLayout(excl_btns)

        layout.addWidget(excl_group)

        # ── Progress ──────────────────────────────────────────────
        self.status_label = QLabel("Idle.")
        self.status_label.setObjectName("muted")
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)

        layout.addStretch()

        self._refresh_dirs_list()

    # ── Helpers ───────────────────────────────────────────────────

    def _get_exclusions(self) -> set[str]:
        lines = self.excl_edit.toPlainText().splitlines()
        return {ln.strip().lower() for ln in lines if ln.strip()}

    def _reset_exclusions(self) -> None:
        self.excl_edit.setPlainText("\n".join(sorted(DEFAULT_EXCLUDED_FOLDERS)))

    def _refresh_dirs_list(self) -> None:
        self.dirs_list.clear()
        for d in self.directories_repo.list_directories():
            last = d["last_scanned_at"] or "never"
            item = QListWidgetItem(
                f'[{d["library_type"]}]  {d["path"]}  — last scan: {last}'
            )
            item.setData(Qt.UserRole, d["id"])
            item.setData(Qt.UserRole + 1, d["path"])
            self.dirs_list.addItem(item)

    # ── Actions ───────────────────────────────────────────────────

    def browse_directory(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select media root")
        if path:
            self.path_input.setText(path)

    def remove_selected_directory(self) -> None:
        item = self.dirs_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Nothing selected", "Select a directory first.")
            return
        dir_id = item.data(Qt.UserRole)
        path = item.data(Qt.UserRole + 1)
        reply = QMessageBox.question(
            self, "Remove Directory",
            f"Remove '{path}' from the library?\n\nFiles will NOT be deleted from disk.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.directories_repo.remove_directory(dir_id)
            self._refresh_dirs_list()
            self.status_label.setText(f"Removed: {path}")

    def rescan_selected(self) -> None:
        item = self.dirs_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Nothing selected", "Select a directory to rescan.")
            return
        self.current_directory_id = item.data(Qt.UserRole)
        path = item.data(Qt.UserRole + 1)
        self._start_scan(self.current_directory_id, path)

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

        self.path_input.clear()
        self._refresh_dirs_list()
        self._start_scan(match["id"], path)

    def _start_scan(self, directory_id: int, path: str) -> None:
        self.worker = ScanWorker(
            directory_id=directory_id,
            root_path=path,
            valid_exts=self.config.supported_video_exts,
            excluded_folders=self._get_exclusions(),
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.finished_scan.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)

        self.progress.show()
        self.scan_btn.setText("Stop Scan")
        self.status_label.setText(f"Scanning: {path}")
        self.worker.start()

    def on_progress(self, count: int, name: str) -> None:
        self.status_label.setText(f"Scanned {count} files... {name}")

    def on_finished(self, result: dict) -> None:
        self.progress.hide()
        self.scan_btn.setText("Add & Scan")
        added = result["files_added"]
        removed = result["files_removed"]
        status = result["status"].capitalize()
        self.status_label.setText(
            f'{status}: {result["files_seen"]} seen, {added} added, {removed} removed.'
        )
        self._refresh_dirs_list()

    def on_failed(self, message: str) -> None:
        self.progress.hide()
        self.scan_btn.setText("Add & Scan")
        self.status_label.setText("Scan failed.")
        QMessageBox.critical(self, "Scan failed", message)