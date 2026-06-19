from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class DashboardView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("Dashboard")
        title.setObjectName("h1")
        subtitle = QLabel("Statistics, charts, and health summaries will appear here.")
        subtitle.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()