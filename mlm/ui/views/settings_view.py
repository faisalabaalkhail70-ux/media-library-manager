from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFormLayout,
    QLineEdit, QPushButton, QGroupBox, QMessageBox
)
from mlm.db.repositories.settings_repo import SettingsRepository


class SettingsView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.settings = SettingsRepository()

        layout = QVBoxLayout(self)

        title = QLabel("Settings")
        title.setObjectName("h1")
        layout.addWidget(title)

        group = QGroupBox("Application Settings")
        form = QFormLayout(group)

        self.tmdb_key = QLineEdit()
        self.tmdb_key.setPlaceholderText("Enter TMDB API key")
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

        form.addRow("TMDB API Key:", self.tmdb_key)
        form.addRow("Plex URL:", self.plex_url)
        form.addRow("Plex Token:", self.plex_token)
        form.addRow("FFprobe Path:", self.ffprobe_path)
        form.addRow("Rename Template:", self.rename_template)

        layout.addWidget(group)

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

    def save_settings(self) -> None:
        self.settings.set("tmdb_api_key", self.tmdb_key.text().strip())
        self.settings.set("plex_url", self.plex_url.text().strip())
        self.settings.set("plex_token", self.plex_token.text().strip())
        self.settings.set("ffprobe_path", self.ffprobe_path.text().strip() or "ffprobe")
        self.settings.set(
            "rename_template",
            self.rename_template.text().strip() or "{Title} ({Year}){Ext}",
        )
        QMessageBox.information(self, "Saved", "Settings saved successfully.")