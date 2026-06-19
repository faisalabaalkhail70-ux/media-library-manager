from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QTableView
from mlm.ui.models.media_files_model import MediaFilesTableModel
from mlm.db.connection import get_connection

class ShowsView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.model = MediaFilesTableModel([])

        layout = QVBoxLayout(self)
        title = QLabel("TV Shows")
        title.setObjectName("h1")
        layout.addWidget(title)

        tools = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_rows)
        tools.addWidget(self.refresh_btn)
        tools.addStretch()
        layout.addLayout(tools)

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.load_rows()

    def load_rows(self) -> None:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    mf.id, mf.file_name, mf.file_path, mf.file_size_bytes, mf.modified_at,
                    mf.resolution, mf.video_codec,
                    me.title AS matched_title, me.release_year
                FROM media_files mf
                JOIN media_entities me ON me.id = mf.entity_id
                WHERE me.media_type = 'show' AND mf.removed_at IS NULL
                ORDER BY mf.id DESC
                LIMIT 5000
                """
            ).fetchall()
        self.model.set_rows([dict(r) for r in rows])