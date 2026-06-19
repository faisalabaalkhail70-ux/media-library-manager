from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFormLayout,
    QLineEdit, QPushButton, QGroupBox
)

class SettingsView(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        title = QLabel("Settings")
        title.setObjectName("h1")
        layout.addWidget(title)

        group = QGroupBox("Application Settings")
        form = QFormLayout(group)

        self.tmdb_key = QLineEdit()
        self.tmdb_key.setPlaceholderText("Enter TMDB API key")

        self.plex_url = QLineEdit()
        self.plex_url.setPlaceholderText("http://127.0.0.1:32400")

        self.plex_token = QLineEdit()
        self.plex_token.setPlaceholderText("Enter Plex token")

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
        layout.addWidget(self.save_btn)

        layout.addStretch()