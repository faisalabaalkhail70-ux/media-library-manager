from __future__ import annotations

import os
import sys
import subprocess

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFormLayout,
    QLineEdit, QPushButton, QGroupBox, QMessageBox,
    QComboBox, QApplication, QHBoxLayout, QProgressBar,
    QTextEdit, QDialog, QDialogButtonBox, QScrollArea
)
from mlm.db.repositories.settings_repo import SettingsRepository
from mlm.ui.styles import get_stylesheet
from mlm.__version__ import VERSION


# ──────────────────────────────────────────────────────────────────────────────────
# Background workers
# ──────────────────────────────────────────────────────────────────────────────────

class _CheckWorker(QThread):
    """Runs check_for_update() off the UI thread."""
    update_found    = Signal(dict)   # emits release metadata
    up_to_date      = Signal()
    check_failed    = Signal(str)    # emits error message

    def run(self) -> None:
        try:
            from mlm.services.updater_service import check_for_update
            result = check_for_update()
            if result:
                self.update_found.emit(result)
            else:
                self.up_to_date.emit()
        except Exception as exc:  # noqa: BLE001
            self.check_failed.emit(str(exc))


class _DownloadWorker(QThread):
    """Streams the zip and extracts it, reporting progress."""
    progress    = Signal(int, int)   # bytes_done, total_bytes
    finished_ok = Signal()
    failed      = Signal(str)

    def __init__(self, zip_url: str) -> None:
        super().__init__()
        self._zip_url = zip_url

    def run(self) -> None:
        try:
            from mlm.services.updater_service import download_and_install
            download_and_install(self._zip_url, progress_cb=self.progress.emit)
            self.finished_ok.emit()
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# ──────────────────────────────────────────────────────────────────────────────────
# "Restart required" dialog  (shown after a successful install)
# ──────────────────────────────────────────────────────────────────────────────────

class _RestartDialog(QDialog):
    """Asks the user to restart immediately or later."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Restart Required")
        self.setMinimumWidth(400)

        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        icon_lbl = QLabel("✅  Update installed successfully!")
        icon_lbl.setStyleSheet("font-size: 14px; color: #81c784; font-weight: bold;")
        lay.addWidget(icon_lbl)

        msg = QLabel(
            "The update has been downloaded and applied.\n"
            "A restart is required for the changes to take effect."
        )
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #b0b0c8; font-size: 12px;")
        lay.addWidget(msg)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        restart_btn = QPushButton("🔄  Restart Now")
        restart_btn.setObjectName("primary")
        restart_btn.setFixedHeight(34)
        restart_btn.clicked.connect(self._restart_app)

        later_btn = QPushButton("Later")
        later_btn.setFixedHeight(34)
        later_btn.clicked.connect(self.accept)

        btn_row.addWidget(restart_btn)
        btn_row.addWidget(later_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

    @staticmethod
    def _restart_app() -> None:
        """Re-launch the current process and exit cleanly."""
        # Re-launch using the same Python interpreter and arguments
        subprocess.Popen([sys.executable] + sys.argv)
        QApplication.instance().quit()


# ──────────────────────────────────────────────────────────────────────────────────
# "Update available" dialog
# ──────────────────────────────────────────────────────────────────────────────────

class _UpdateDialog(QDialog):
    """Shows release notes and offers Download & Install or Skip."""

    def __init__(self, release: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Update Available \u2014 {release['name']}")
        self.setMinimumWidth(520)
        self._release   = release
        self._worker: _DownloadWorker | None = None

        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        # Header
        hdr = QLabel(f"\U0001f389  Version <b>{release['tag']}</b> is available!")
        hdr.setStyleSheet("font-size: 14px; color: #81c784; padding: 4px 0;")
        lay.addWidget(hdr)

        cur_lbl = QLabel(f"Your current version: <b>{VERSION}</b>")
        cur_lbl.setStyleSheet("color: #9e9e9e; font-size: 12px;")
        lay.addWidget(cur_lbl)

        # Release notes
        notes_lbl = QLabel("Release notes:")
        notes_lbl.setStyleSheet("font-weight: bold; margin-top: 6px;")
        lay.addWidget(notes_lbl)

        notes = QTextEdit()
        notes.setReadOnly(True)
        notes.setPlainText(release["body"])
        notes.setFixedHeight(160)
        lay.addWidget(notes)

        # Progress bar (hidden until download starts)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        lay.addWidget(self._progress)

        self._status = QLabel("")
        self._status.setObjectName("muted")
        lay.addWidget(self._status)

        # Buttons
        self._install_btn = QPushButton("\u2b07\ufe0f  Download & Install")
        self._install_btn.setObjectName("primary")
        self._install_btn.clicked.connect(self._start_download)

        skip_btn = QPushButton("Skip this version")
        skip_btn.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._install_btn)
        btn_row.addWidget(skip_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

    def closeEvent(self, event) -> None:  # noqa: N802
        """Ensure download thread is stopped if dialog is closed mid-download."""
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(3000)
        super().closeEvent(event)

    def _start_download(self) -> None:
        self._install_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._status.setText("Downloading update\u2026")

        self._worker = _DownloadWorker(self._release["zip_url"])
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_progress(self, done: int, total: int) -> None:
        if total > 0:
            self._progress.setRange(0, 100)
            self._progress.setValue(int(done / total * 100))
        else:
            self._progress.setRange(0, 0)
        mb = done / (1024 * 1024)
        self._status.setText(f"Downloading\u2026 {mb:.1f} MB")

    def _on_done(self) -> None:
        self._progress.setValue(100)
        self._status.setText("")
        # Close the download dialog first, then show the restart prompt
        self.accept()
        dlg = _RestartDialog(self.parent())
        dlg.exec()

    def _on_failed(self, msg: str) -> None:
        self._install_btn.setEnabled(True)
        self._progress.setVisible(False)
        self._status.setText(f"Error: {msg}")
        QMessageBox.critical(self, "Download Failed", f"Could not download update:\n{msg}")


# ──────────────────────────────────────────────────────────────────────────────────
# Main settings view
# ──────────────────────────────────────────────────────────────────────────────────

class SettingsView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.settings = SettingsRepository()
        self._check_worker: _CheckWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Settings")
        title.setObjectName("h1")
        layout.addWidget(title)

        # \u2500\u2500 API / Integration
        api_group = QGroupBox("API & Integration")
        api_form = QFormLayout(api_group)

        self.tmdb_key = QLineEdit()
        self.tmdb_key.setPlaceholderText("TMDB Read Access Token (Bearer)")
        self.tmdb_key.setEchoMode(QLineEdit.Password)

        self.plex_url = QLineEdit()
        self.plex_url.setPlaceholderText("http://127.0.0.1:32400")

        self.plex_token = QLineEdit()
        self.plex_token.setPlaceholderText("Enter Plex token")
        self.plex_token.setEchoMode(QLineEdit.Password)

        self.ffprobe_path = QLineEdit()
        self.ffprobe_path.setPlaceholderText("ffprobe")

        self.rename_template = QLineEdit()
        self.rename_template.setPlaceholderText("{Title} ({Year}){Ext}")

        api_form.addRow("TMDB API Key:", self.tmdb_key)
        api_form.addRow("Plex URL:", self.plex_url)
        api_form.addRow("Plex Token:", self.plex_token)
        api_form.addRow("FFprobe Path:", self.ffprobe_path)
        api_form.addRow("Rename Template:", self.rename_template)
        layout.addWidget(api_group)

        # \u2500\u2500 Appearance
        appear_group = QGroupBox("Appearance")
        appear_form = QFormLayout(appear_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])

        self.density_combo = QComboBox()
        self.density_combo.addItems(["Comfortable (28 px)", "Compact (20 px)"])

        appear_form.addRow("Theme:", self.theme_combo)
        appear_form.addRow("Row Density:", self.density_combo)
        layout.addWidget(appear_group)

        # \u2500\u2500 Updates
        update_group = QGroupBox("Application Updates")
        update_layout = QVBoxLayout(update_group)
        update_layout.setSpacing(8)

        ver_row = QHBoxLayout()
        ver_row.addWidget(QLabel("Current version:"))
        ver_lbl = QLabel(f"<b>{VERSION}</b>")
        ver_lbl.setStyleSheet("color: #81c784;")
        ver_row.addWidget(ver_lbl)
        ver_row.addStretch()
        update_layout.addLayout(ver_row)

        btn_row = QHBoxLayout()
        self._check_btn = QPushButton("\U0001f504  Check for Updates")
        self._check_btn.setObjectName("primary")
        self._check_btn.setFixedWidth(200)
        self._check_btn.clicked.connect(self._check_updates)
        btn_row.addWidget(self._check_btn)

        self._update_status = QLabel("")
        self._update_status.setObjectName("muted")
        btn_row.addWidget(self._update_status)
        btn_row.addStretch()
        update_layout.addLayout(btn_row)

        layout.addWidget(update_group)

        # \u2500\u2500 Save
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_btn)

        layout.addStretch()
        self._load_settings()

    # \u2500\u2500 Update logic \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    def _check_updates(self) -> None:
        if self._check_worker and self._check_worker.isRunning():
            return
        self._check_btn.setEnabled(False)
        self._update_status.setText("Checking\u2026")
        self._update_status.setStyleSheet("color: #9e9e9e;")

        self._check_worker = _CheckWorker()
        self._check_worker.update_found.connect(self._on_update_found)
        self._check_worker.up_to_date.connect(self._on_up_to_date)
        self._check_worker.check_failed.connect(self._on_check_failed)
        self._check_worker.finished.connect(lambda: self._check_btn.setEnabled(True))
        self._check_worker.start()

    def _on_update_found(self, release: dict) -> None:
        self._update_status.setText(f"\u2b06\ufe0f  {release['tag']} available")
        self._update_status.setStyleSheet("color: #81c784; font-weight: bold;")
        dlg = _UpdateDialog(release, parent=self)
        dlg.exec()

    def _on_up_to_date(self) -> None:
        self._update_status.setText("\u2705  You're up to date!")
        self._update_status.setStyleSheet("color: #81c784;")

    def _on_check_failed(self, msg: str) -> None:
        self._update_status.setText(f"\u274c  Check failed: {msg}")
        self._update_status.setStyleSheet("color: #ef9a9a;")

    # \u2500\u2500 Settings logic \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    def _load_settings(self) -> None:
        self.tmdb_key.setText(self.settings.get("tmdb_api_key", ""))
        self.plex_url.setText(self.settings.get("plex_url", ""))
        self.plex_token.setText(self.settings.get("plex_token", ""))
        self.ffprobe_path.setText(self.settings.get("ffprobe_path", "ffprobe"))
        self.rename_template.setText(
            self.settings.get("rename_template", "{Title} ({Year}){Ext}")
        )
        theme = self.settings.get("ui_theme", "dark")
        self.theme_combo.setCurrentIndex(0 if theme == "dark" else 1)

        density = self.settings.get("ui_row_density", "comfortable")
        self.density_combo.setCurrentIndex(0 if density == "comfortable" else 1)

    def closeEvent(self, event) -> None:  # noqa: N802
        """Stop any running workers before the widget is destroyed."""
        if self._check_worker and self._check_worker.isRunning():
            self._check_worker.quit()
            self._check_worker.wait(2000)
        super().closeEvent(event)

    def save_settings(self) -> None:
        self.settings.set("tmdb_api_key",    self.tmdb_key.text().strip())
        self.settings.set("plex_url",         self.plex_url.text().strip())
        self.settings.set("plex_token",       self.plex_token.text().strip())
        self.settings.set("ffprobe_path",     self.ffprobe_path.text().strip() or "ffprobe")
        self.settings.set("rename_template",
            self.rename_template.text().strip() or "{Title} ({Year}){Ext}")

        theme = "light" if self.theme_combo.currentIndex() == 1 else "dark"
        self.settings.set("ui_theme", theme)
        QApplication.instance().setStyleSheet(get_stylesheet(theme))

        density = "compact" if self.density_combo.currentIndex() == 1 else "comfortable"
        self.settings.set("ui_row_density", density)
        self._apply_density(density)

        QMessageBox.information(self, "Saved", "Settings saved. Theme and density applied immediately.")

    def _apply_density(self, density: str) -> None:
        from PySide6.QtWidgets import QTableView, QTableWidget
        row_height = 20 if density == "compact" else 28
        for widget in QApplication.instance().allWidgets():
            if isinstance(widget, (QTableView, QTableWidget)):
                widget.verticalHeader().setDefaultSectionSize(row_height)
