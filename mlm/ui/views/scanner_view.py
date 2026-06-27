import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
    QFileDialog, QLineEdit, QMessageBox, QComboBox, QProgressBar,
    QListWidget, QListWidgetItem, QGroupBox, QPlainTextEdit
)
from PySide6.QtCore import Qt
from mlm.app.config import AppConfig
from mlm.db.repositories.directories_repo import DirectoriesRepository
from mlm.workers.scan_worker import ScanWorker, DEFAULT_EXCLUDED_FOLDERS
from mlm.db.connection import get_connection


def _pick_multiple_directories(parent: QWidget, title: str = "Select media folders") -> list[str]:
    """Show a folder picker that lets the user select multiple directories.

    Qt's native folder dialog only returns one path.  We work around this by
    re-opening the dialog in a loop: each accepted path is collected and the
    dialog reopens pre-set to the last chosen location so the user can quickly
    navigate to the next folder.  The loop ends when the user cancels.

    Returns a (possibly empty) list of unique, non-empty directory paths.
    """
    selected: list[str] = []
    start_dir = ""
    while True:
        path = QFileDialog.getExistingDirectory(
            parent,
            f"{title} ({len(selected)} selected — Cancel to finish)",
            start_dir or os.path.expanduser("~"),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )
        if not path:
            # User cancelled → done collecting
            break
        if path not in selected:
            selected.append(path)
        start_dir = os.path.dirname(path)  # re-open near last selection
    return selected


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

        # ── Add Directory ────────────────────────────────────────────────
        add_group = QGroupBox("Add Directory")
        add_layout = QVBoxLayout(add_group)

        row = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select one or more media root directories...")
        browse_btn = QPushButton("Browse")
        browse_btn.setToolTip(
            "Click Browse to pick a folder.\n"
            "Pick as many folders as you like — a new dialog opens after each one.\n"
            "Cancel the dialog when you are done."
        )
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

        # ── Registered Directories ───────────────────────────────────────
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

        # ── Excluded Folder Names ───────────────────────────────────────
        excl_group = QGroupBox("Excluded Folder Names")
        excl_layout = QVBoxLayout(excl_group)

        excl_note = QLabel(
            "Folder names to skip during scan (case-insensitive, one per line).\n"
            "Use \"Exclude a Specific Folder\" to skip a full path."
        )
        excl_note.setObjectName("muted")
        excl_note.setWordWrap(True)
        excl_layout.addWidget(excl_note)

        self.excl_edit = QPlainTextEdit()
        self.excl_edit.setFixedHeight(100)
        self.excl_edit.setPlainText("\n".join(sorted(DEFAULT_EXCLUDED_FOLDERS)))
        excl_layout.addWidget(self.excl_edit)

        excl_btns = QHBoxLayout()
        reset_excl_btn = QPushButton("Reset to Defaults")
        reset_excl_btn.clicked.connect(self._reset_exclusions)

        browse_excl_btn = QPushButton("Exclude a Specific Folder…")
        browse_excl_btn.clicked.connect(self._browse_excluded_folder)

        excl_btns.addWidget(reset_excl_btn)
        excl_btns.addWidget(browse_excl_btn)
        excl_btns.addStretch()
        excl_layout.addLayout(excl_btns)

        layout.addWidget(excl_group)

        # ── Progress ───────────────────────────────────────────────────
        self.status_label = QLabel("Idle.")
        self.status_label.setObjectName("muted")
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)

        layout.addStretch()
        self._refresh_dirs_list()

    # ── Helpers ───────────────────────────────────────────────

    def _get_exclusions(self) -> tuple[set[str], set[str]]:
        names: set[str] = set()
        paths: set[str] = set()
        for ln in self.excl_edit.toPlainText().splitlines():
            ln = ln.strip()
            if not ln:
                continue
            from pathlib import Path as _Path
            if _Path(ln).is_absolute() or ("/" in ln or "\\" in ln):
                paths.add(ln)
            else:
                names.add(ln.lower())
        return names, paths

    def _reset_exclusions(self) -> None:
        self.excl_edit.setPlainText("\n".join(sorted(DEFAULT_EXCLUDED_FOLDERS)))

    def _browse_excluded_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select folder to exclude")
        if not path:
            return
        existing_lines = [ln.strip() for ln in self.excl_edit.toPlainText().splitlines()]
        if path not in existing_lines:
            existing_lines.append(path)
            self.excl_edit.setPlainText("\n".join(filter(None, existing_lines)))

    def _refresh_dirs_list(self) -> None:
        self.dirs_list.clear()
        for d in self.directories_repo.list_directories():
            last = d["last_scanned_at"] or "never"
            item = QListWidgetItem(
                f'[{d["library_type"]}]  {d["path"]}  — last scan: {last}'
            )
            item.setData(Qt.UserRole,     d["id"])
            item.setData(Qt.UserRole + 1, d["path"])
            self.dirs_list.addItem(item)

    # ── Actions ───────────────────────────────────────────────

    def browse_directory(self) -> None:
        """Open a loop-based multi-folder picker and populate path_input.

        All selected paths are joined with os.pathsep so toggle_scan()
        can split and register them individually.
        """
        paths = _pick_multiple_directories(self, "Select media root folders")
        if paths:
            self.path_input.setText(os.pathsep.join(paths))

    def remove_selected_directory(self) -> None:
        item = self.dirs_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Nothing selected", "Select a directory first.")
            return
        dir_id = item.data(Qt.UserRole)
        path   = item.data(Qt.UserRole + 1)
        reply  = QMessageBox.question(
            self, "Remove Directory",
            f"Remove '{path}' from the library?\n\n"
            "All scanned file records for this directory will be removed from the database.\n"
            "Files on disk will NOT be deleted.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        with get_connection() as conn:
            file_ids = [
                r["id"] for r in conn.execute(
                    "SELECT id FROM media_files WHERE directory_id = ?", (dir_id,)
                ).fetchall()
            ]

            if file_ids:
                ph = ",".join("?" * len(file_ids))
                conn.execute(
                    f"UPDATE episodes SET media_file_id = NULL, is_missing = 1 "
                    f"WHERE media_file_id IN ({ph})",
                    file_ids,
                )
                conn.execute(
                    f"DELETE FROM duplicate_items WHERE media_file_id IN ({ph})",
                    file_ids,
                )
                conn.execute(
                    f"UPDATE action_ledger SET media_file_id = NULL "
                    f"WHERE media_file_id IN ({ph})",
                    file_ids,
                )

            conn.execute(
                "DELETE FROM media_files WHERE directory_id = ?", (dir_id,)
            )
            conn.execute(
                """
                DELETE FROM duplicate_groups
                WHERE id NOT IN (SELECT DISTINCT group_id FROM duplicate_items)
                """
            )

            orphan_entity_ids = [
                r["id"] for r in conn.execute(
                    """
                    SELECT id FROM media_entities
                    WHERE id NOT IN (
                        SELECT DISTINCT entity_id FROM media_files
                        WHERE entity_id IS NOT NULL
                    )
                    """
                ).fetchall()
            ]

            if orphan_entity_ids:
                eph = ",".join("?" * len(orphan_entity_ids))
                conn.execute(
                    f"DELETE FROM episodes WHERE entity_id IN ({eph})",
                    orphan_entity_ids,
                )
                conn.execute(
                    f"DELETE FROM media_entities WHERE id IN ({eph})",
                    orphan_entity_ids,
                )

            conn.execute("DELETE FROM scan_runs WHERE directory_id = ?", (dir_id,))
            conn.execute("DELETE FROM directories WHERE id = ?", (dir_id,))

        self._refresh_dirs_list()
        self.status_label.setText(f"Removed: {path}")

        from PySide6.QtWidgets import QApplication
        main_win = QApplication.instance().activeWindow()
        if main_win and hasattr(main_win, "stack"):
            stack = main_win.stack
            for i in range(stack.count()):
                w = stack.widget(i)
                if hasattr(w, "load_rows"):
                    w.load_rows()

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

        raw = self.path_input.text().strip()
        if not raw:
            QMessageBox.warning(self, "Missing folder", "Choose a directory first.")
            return

        # Support multiple paths joined by os.pathsep (from browse_directory)
        paths = [p.strip() for p in raw.split(os.pathsep) if p.strip()]
        library_type = self.type_combo.currentText()

        # Register all selected directories first
        registered = []
        for path in paths:
            self.directories_repo.add_directory(path, library_type)
            directories = self.directories_repo.list_directories()
            match = next((d for d in directories if d["path"] == path), None)
            if match:
                registered.append((match["id"], path))
            else:
                QMessageBox.critical(self, "Error", f"Failed to register directory: {path}")

        if not registered:
            return

        self.path_input.clear()
        self._refresh_dirs_list()

        # Start scan for the first registered directory;
        # subsequent directories can be rescanned from the list.
        dir_id, first_path = registered[0]
        self._start_scan(dir_id, first_path)

        if len(registered) > 1:
            remaining = ", ".join(p for _, p in registered[1:])
            QMessageBox.information(
                self, "Multiple Folders Added",
                f"{len(registered)} folders registered.\n\n"
                f"Scanning: {first_path}\n\n"
                f"To scan the remaining folders, select each one in the "
                f"Registered Directories list and click Rescan Selected.\n\n"
                f"Remaining: {remaining}"
            )

    def _start_scan(self, directory_id: int, path: str) -> None:
        name_excl, path_excl = self._get_exclusions()
        self.worker = ScanWorker(
            directory_id=directory_id,
            root_path=path,
            valid_exts=self.config.supported_video_exts,
            excluded_folders=name_excl,
            excluded_paths=path_excl,
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
        added   = result["files_added"]
        removed = result["files_removed"]
        status  = result["status"].capitalize()
        self.status_label.setText(
            f'{status}: {result["files_seen"]} seen, {added} added, {removed} removed.'
        )
        self._refresh_dirs_list()

    def on_failed(self, message: str) -> None:
        self.progress.hide()
        self.scan_btn.setText("Add & Scan")
        self.status_label.setText("Scan failed.")
        QMessageBox.critical(self, "Scan failed", message)
