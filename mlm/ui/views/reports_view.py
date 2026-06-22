"""Reports & Export view — CSV / JSON / Excel / PDF with timestamped filenames."""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
    QGroupBox, QComboBox, QMessageBox, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt
from mlm.services.export_service import ExportService
from mlm.app.paths import EXPORT_DIR


REPORT_OPTIONS = [
    ("Library",          "library"),
    ("Missing Episodes", "missing_episodes"),
    ("Duplicates",       "duplicates"),
    ("Watchlist",        "watchlist"),
]


class ReportsView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.export_service = ExportService()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Reports & Export")
        title.setObjectName("h1")
        layout.addWidget(title)

        # ── Export group ───────────────────────────────────────────────
        export_group = QGroupBox("Export Report")
        export_layout = QVBoxLayout(export_group)

        row = QHBoxLayout()
        self.report_combo = QComboBox()
        for label, _ in REPORT_OPTIONS:
            self.report_combo.addItem(label)

        self.csv_btn   = QPushButton("Export CSV")
        self.csv_btn.clicked.connect(lambda: self._export("csv"))

        self.json_btn  = QPushButton("Export JSON")
        self.json_btn.clicked.connect(lambda: self._export("json"))

        self.excel_btn = QPushButton("Export Excel")
        self.excel_btn.clicked.connect(lambda: self._export("excel"))

        self.pdf_btn   = QPushButton("Export PDF")
        self.pdf_btn.clicked.connect(lambda: self._export("pdf"))

        row.addWidget(QLabel("Report:"))
        row.addWidget(self.report_combo, 1)
        row.addWidget(self.csv_btn)
        row.addWidget(self.json_btn)
        row.addWidget(self.excel_btn)
        row.addWidget(self.pdf_btn)
        export_layout.addLayout(row)

        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")
        self.status_label.setWordWrap(True)
        export_layout.addWidget(self.status_label)

        layout.addWidget(export_group)

        # ── Previous exports ───────────────────────────────────────────
        prev_group = QGroupBox("Previous Exports")
        prev_layout = QVBoxLayout(prev_group)

        self.exports_list = QListWidget()
        self.exports_list.setFixedHeight(200)
        prev_layout.addWidget(self.exports_list)

        btns = QHBoxLayout()
        open_btn = QPushButton("Open Selected")
        open_btn.clicked.connect(self._open_selected)
        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self._delete_selected)
        refresh_btn = QPushButton("Refresh List")
        refresh_btn.clicked.connect(self._refresh_exports)
        btns.addWidget(open_btn)
        btns.addWidget(delete_btn)
        btns.addWidget(refresh_btn)
        btns.addStretch()
        prev_layout.addLayout(btns)

        layout.addWidget(prev_group)
        layout.addStretch()

        self._refresh_exports()

    # ── Helpers ──────────────────────────────────────────────────

    def _selected_report_key(self) -> str:
        idx = self.report_combo.currentIndex()
        return REPORT_OPTIONS[idx][1]

    def _export(self, fmt: str) -> None:
        report_key = self._selected_report_key()
        try:
            if fmt == "csv":
                path = self.export_service.export_csv(report_key)
            elif fmt == "json":
                path = self.export_service.export_json(report_key)
            elif fmt == "excel":
                path = self.export_service.export_excel(report_key)
            else:
                path = self.export_service.export_pdf(report_key)
            self.status_label.setText(f"\u2713 Exported: {path}")
            self._refresh_exports()
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    def _refresh_exports(self) -> None:
        self.exports_list.clear()
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        files = sorted(EXPORT_DIR.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
        for f in files:
            if f.is_file():
                size_kb = f.stat().st_size // 1024
                item = QListWidgetItem(f"{f.name}  ({size_kb} KB)")
                item.setData(Qt.UserRole, str(f))
                self.exports_list.addItem(item)

    def _open_selected(self) -> None:
        item = self.exports_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Nothing selected", "Select a file to open.")
            return
        path = item.data(Qt.UserRole)
        os.startfile(path)

    def _delete_selected(self) -> None:
        item = self.exports_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Nothing selected", "Select a file to delete.")
            return
        path = item.data(Qt.UserRole)
        reply = QMessageBox.question(
            self, "Delete Export",
            f"Delete {os.path.basename(path)}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                os.remove(path)
                self._refresh_exports()
            except OSError as e:
                QMessageBox.critical(self, "Error", str(e))
