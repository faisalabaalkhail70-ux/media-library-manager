"""Column visibility AND width persistence helpers.

Usage::

    from mlm.ui.column_visibility import (
        ColumnVisibilityDialog, apply_saved_visibility,
        save_column_widths, restore_column_widths, install_width_autosave,
    )

    # On view init
    restore_column_widths(self.table, "shows")
    install_width_autosave(self.table, "shows")   # auto-saves on every drag
    apply_saved_visibility(self.table, "shows")

All state is stored in app_settings:
  col_vis_{name}    → JSON bool list  (visibility)
  col_wid_{name}    → JSON int list   (pixel widths)
"""
import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QCheckBox,
    QPushButton, QLabel, QTableView, QTableWidget
)
from PySide6.QtCore import Qt
from mlm.db.repositories.settings_repo import SettingsRepository


# ──────────────────────────────────────────────────────────────────────────────────
# Column visibility
# ──────────────────────────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────────────────────────
# Column width persistence
# ──────────────────────────────────────────────────────────────────────────────────

def save_column_widths(table, table_name: str) -> None:
    """Snapshot current column pixel widths to settings."""
    header = table.horizontalHeader()
    widths = [header.sectionSize(i) for i in range(header.count())]
    SettingsRepository().set(f"col_wid_{table_name}", json.dumps(widths))


def restore_column_widths(table, table_name: str) -> None:
    """Restore previously saved column widths (if count matches)."""
    raw = SettingsRepository().get(f"col_wid_{table_name}", "")
    if not raw:
        return
    try:
        widths = json.loads(raw)
    except Exception:
        return
    header = table.horizontalHeader()
    if len(widths) != header.count():
        return
    # Temporarily disable stretch-last so widths are honoured exactly
    header.setStretchLastSection(False)
    for i, w in enumerate(widths):
        if w > 0:
            header.resizeSection(i, w)
    header.setStretchLastSection(True)


def install_width_autosave(table, table_name: str) -> None:
    """Connect sectionResized so every drag automatically persists widths.

    Uses a single-shot debounce: rapid consecutive resize events only
    trigger one DB write (after the user stops dragging).
    """
    from PySide6.QtCore import QTimer
    _timer = QTimer()
    _timer.setSingleShot(True)
    _timer.setInterval(400)   # 400 ms debounce
    _timer.timeout.connect(lambda: save_column_widths(table, table_name))

    def _on_resize(_logical, _old, _new):
        _timer.start()   # restart debounce on every resize event

    table.horizontalHeader().sectionResized.connect(_on_resize)
    # Keep timer alive by parenting it to the table widget
    _timer.setParent(table)
