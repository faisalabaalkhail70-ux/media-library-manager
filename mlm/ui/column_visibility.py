"""Column visibility dialog and per-table persistence.

Usage in any view::

    from mlm.ui.column_visibility import ColumnVisibilityButton
    btn = ColumnVisibilityButton(self.table, "movies", toolbar_layout)

This adds a ⚙ Columns button that opens a checkbox dialog. The user's
choices are saved to app_settings under the key `col_vis_{table_name}`
and restored on next launch.
"""
import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QCheckBox,
    QPushButton, QLabel, QTableView, QTableWidget
)
from PySide6.QtCore import Qt
from mlm.db.repositories.settings_repo import SettingsRepository


class ColumnVisibilityDialog(QDialog):
    def __init__(self, table, table_name: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Show / Hide Columns")
        self.setModal(True)
        self.table = table
        self.table_name = table_name
        self.settings = SettingsRepository()

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        lbl = QLabel("Choose which columns to display:")
        lbl.setObjectName("muted")
        layout.addWidget(lbl)

        model = table.model() if hasattr(table, "model") else None
        col_count = model.columnCount() if model else table.columnCount()

        self._checkboxes: list[QCheckBox] = []
        saved = self._load_visibility(col_count)

        for col in range(col_count):
            if model:
                header_text = model.headerData(col, Qt.Horizontal)
            else:
                header_text = table.horizontalHeaderItem(col)
                header_text = header_text.text() if header_text else str(col)
            cb = QCheckBox(str(header_text))
            cb.setChecked(saved[col])
            self._checkboxes.append(cb)
            layout.addWidget(cb)

        btns = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        apply_btn.setObjectName("primary")
        apply_btn.clicked.connect(self._apply)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(apply_btn)
        layout.addLayout(btns)

    def _load_visibility(self, col_count: int) -> list[bool]:
        raw = self.settings.get(f"col_vis_{self.table_name}", "")
        try:
            saved = json.loads(raw)
            if len(saved) == col_count:
                return saved
        except Exception:
            pass
        return [True] * col_count

    def _apply(self) -> None:
        visibility = [cb.isChecked() for cb in self._checkboxes]
        for col, visible in enumerate(visibility):
            self.table.setColumnHidden(col, not visible)
        self.settings.set(
            f"col_vis_{self.table_name}",
            json.dumps(visibility),
        )
        self.accept()


def apply_saved_visibility(table, table_name: str) -> None:
    """Restore saved column visibility on view startup."""
    settings = SettingsRepository()
    model = table.model() if hasattr(table, "model") else None
    col_count = model.columnCount() if model else table.columnCount()
    raw = settings.get(f"col_vis_{table_name}", "")
    try:
        visibility = json.loads(raw)
        if len(visibility) == col_count:
            for col, visible in enumerate(visibility):
                table.setColumnHidden(col, not visible)
    except Exception:
        pass
