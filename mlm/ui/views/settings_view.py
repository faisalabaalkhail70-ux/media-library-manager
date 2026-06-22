from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFormLayout,
    QLineEdit, QPushButton, QGroupBox, QMessageBox,
    QComboBox, QApplication
)
from mlm.db.repositories.settings_repo import SettingsRepository
from mlm.ui.styles import get_stylesheet


class SettingsView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.settings = SettingsRepository()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Settings")
        title.setObjectName("h1")
        layout.addWidget(title)

        # ── API / Integration ──────────────────────────────────────────
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

        # ── Appearance ────────────────────────────────────────────────
        appear_group = QGroupBox("Appearance")
        appear_form = QFormLayout(appear_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])

        self.density_combo = QComboBox()
        self.density_combo.addItems(["Comfortable (28 px)", "Compact (20 px)"])

        appear_form.addRow("Theme:", self.theme_combo)
        appear_form.addRow("Row Density:", self.density_combo)
        layout.addWidget(appear_group)

        # ── Save ────────────────────────────────────────────────────────
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_btn)

        layout.addStretch()
        self._load_settings()

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
        """Walk every QTableView/QTableWidget in the app and update row height."""
        from PySide6.QtWidgets import QTableView, QTableWidget
        row_height = 20 if density == "compact" else 28
        for widget in QApplication.instance().allWidgets():
            if isinstance(widget, (QTableView, QTableWidget)):
                widget.verticalHeader().setDefaultSectionSize(row_height)
