"""Smart Rename view — per-row selection with Plex-compatible naming.

New capabilities vs original:
- Checkbox column: user picks exactly which rows to rename
- Select All / Deselect All / Only Valid / Filter by media type buttons
- Plex-compatible template presets with one click
- Apply only acts on *checked* rows regardless of status
- Column width autosave
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
    QLineEdit, QTableView, QMessageBox, QGroupBox, QAbstractItemView,
    QHeaderView
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QColor

from mlm.services.rename_service import RenameService
from mlm.services.undo_service import UndoService
from mlm.db.repositories.settings_repo import SettingsRepository
from mlm.workers.rename_worker import RenameWorker
from mlm.ui.column_visibility import restore_column_widths, install_width_autosave


# ──────────────────────────────────────────────────────────────────────────────────
# Table model with checkbox column
# ──────────────────────────────────────────────────────────────────────────────────

_GREEN   = QColor("#81c784")
_YELLOW  = QColor("#fff176")
_AMBER   = QColor("#ffa726")
_RED     = QColor("#ef9a9a")
_MUTED   = QColor("#6e6e8a")
_NORMAL  = QColor("#d0d0e8")
_DIM     = QColor("#424255")   # background tint for unchecked rows


class RenamePreviewModel(QAbstractTableModel):
    """Preview model with a leading ☑ checkbox column.

    Column layout (col 0 is the checkbox):
      0  ☑
      1  Current Name
      2  Proposed Name
      3  Status
      4  Type           (Movie / Show)
      5  Current Path
      6  New Path
    """

    HEADERS = ["☑", "Current Name", "Proposed Name", "Status", "Type", "Current Path", "New Path"]

    _COL_CHECK   = 0
    _COL_OLD     = 1
    _COL_NEW     = 2
    _COL_STATUS  = 3
    _COL_TYPE    = 4
    _COL_OLD_PATH = 5
    _COL_NEW_PATH = 6

    def __init__(self, rows: list[dict] | None = None) -> None:
        super().__init__()
        self._rows: list[dict] = []
        self._checked: list[bool] = []
        if rows:
            self.set_rows(rows)

    def set_rows(self, rows: list[dict], preserve_paths: set[str] | None = None) -> None:
        """Load rows into the model.

        Parameters
        ----------
        rows:           New preview rows from the rename service.
        preserve_paths: Set of ``old_path`` values whose checked state should
                        be preserved from a previous call.  When provided,
                        any row whose old_path is in the set will be checked
                        even if its status is not 'valid'.  Rows whose
                        old_path is NOT in the set will be unchecked.
                        When None, defaults to auto-checking all 'valid' rows.
        """
        self.beginResetModel()
        self._rows = rows or []
        if preserve_paths is not None:
            self._checked = [r.get("old_path") in preserve_paths for r in self._rows]
        else:
            # Auto-check rows that are 'valid'; leave others unchecked
            self._checked = [r.get("status") == "valid" for r in self._rows]
        self.endResetModel()

    def rows(self) -> list[dict]:
        return self._rows

    def checked_rows(self) -> list[dict]:
        """Return only rows the user has checked."""
        return [r for r, c in zip(self._rows, self._checked) if c]

    def set_all_checked(self, checked: bool) -> None:
        self._checked = [checked] * len(self._rows)
        self.dataChanged.emit(
            self.index(0, self._COL_CHECK),
            self.index(len(self._rows) - 1, self._COL_CHECK),
        )

    def set_checked_by_status(self, status: str) -> None:
        """Check only rows whose status matches *status* (e.g. 'valid')."""
        self._checked = [r.get("status") == status for r in self._rows]
        self.dataChanged.emit(
            self.index(0, self._COL_CHECK),
            self.index(len(self._rows) - 1, self._COL_CHECK),
        )

    def set_checked_by_type(self, media_type: str) -> None:
        """Check only rows whose media type matches (e.g. 'show', 'movie')."""
        self._checked = [
            (r.get("media_type") or "").lower() == media_type.lower()
            for r in self._rows
        ]
        self.dataChanged.emit(
            self.index(0, self._COL_CHECK),
            self.index(len(self._rows) - 1, self._COL_CHECK),
        )

    # ── QAbstractTableModel interface ──────────────────────────────────────────────────

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def flags(self, index: QModelIndex):
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == self._COL_CHECK:
            return base | Qt.ItemIsUserCheckable
        return base

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row     = self._rows[index.row()]
        col     = index.column()
        checked = self._checked[index.row()]
        status  = str(row.get("status", "")).lower()
        mtype   = (row.get("media_type") or "").capitalize()

        if role == Qt.CheckStateRole and col == self._COL_CHECK:
            return Qt.Checked if checked else Qt.Unchecked

        if role == Qt.DisplayRole:
            if col == self._COL_CHECK:    return None
            if col == self._COL_OLD:      return row.get("old_name", "")
            if col == self._COL_NEW:      return row.get("new_name", "")
            if col == self._COL_STATUS:   return status.capitalize()
            if col == self._COL_TYPE:     return mtype
            if col == self._COL_OLD_PATH: return row.get("old_path", "")
            if col == self._COL_NEW_PATH: return row.get("new_path", "")

        if role == Qt.ForegroundRole:
            if col == self._COL_STATUS:
                return {
                    "valid":     _GREEN,
                    "conflict":  _AMBER,
                    "invalid":   _RED,
                    "unchanged": _MUTED,
                }.get(status, _NORMAL)
            if col == self._COL_TYPE:
                if mtype.lower() == "movie": return QColor("#4dd0e1")
                if mtype.lower() == "show":  return _GREEN
                return _MUTED
            if not checked:
                return _MUTED
            return _NORMAL

        if role == Qt.BackgroundRole and not checked:
            return _DIM

        return None

    def setData(self, index: QModelIndex, value, role=Qt.EditRole) -> bool:
        if role == Qt.CheckStateRole and index.column() == self._COL_CHECK:
            self._checked[index.row()] = (value == Qt.Checked)
            self.dataChanged.emit(index, self.index(index.row(), self.columnCount() - 1))
            return True
        return False


# ──────────────────────────────────────────────────────────────────────────────────
# Main view
# ──────────────────────────────────────────────────────────────────────────────────

# Plex-compatible naming presets
_PLEX_PRESETS = [
    ("Plex — Movie",   "{Title} ({Year}){Ext}"),
    ("Plex — TV Show",  "{Title} - S{Season:02}E{Episode:02}{Ext}"),
    ("Plex — TV w/Year", "{Title} ({Year}) - S{Season:02}E{Episode:02}{Ext}"),
    ("Simple",           "{Title}{Ext}"),
]


class RenameView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.rename_service = RenameService()
        self.undo_service   = UndoService()
        self.settings       = SettingsRepository()
        self.model          = RenamePreviewModel()
        self.worker         = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Smart Rename")
        title.setObjectName("h1")
        layout.addWidget(title)

        # ── Template group
        tmpl_group = QGroupBox("Rename Template")
        tmpl_layout = QVBoxLayout(tmpl_group)

        hint = QLabel(
            "Tokens: <b>{Title}</b>  {Year}  {Season:02}  {Episode:02}  {Resolution}  {Ext}<br>"
            "Plex standard: <code>{Title} - S{Season:02}E{Episode:02}{Ext}</code> for TV Shows"
        )
        hint.setObjectName("muted")
        hint.setTextFormat(Qt.RichText)
        hint.setWordWrap(True)
        tmpl_layout.addWidget(hint)

        tmpl_row = QHBoxLayout()
        self.template_input = QLineEdit()
        self.template_input.setPlaceholderText("{Title} ({Year}){Ext}")
        self._load_template()
        tmpl_row.addWidget(self.template_input, 1)

        self.preview_btn = QPushButton("Preview")
        self.preview_btn.setObjectName("primary")
        self.preview_btn.clicked.connect(self.preview)
        tmpl_row.addWidget(self.preview_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_preview)
        tmpl_row.addWidget(self.clear_btn)
        tmpl_layout.addLayout(tmpl_row)

        # Plex preset buttons
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Plex presets:"))
        for label, tmpl in _PLEX_PRESETS:
            btn = QPushButton(label)
            btn.setFixedHeight(26)
            btn.clicked.connect(lambda _=False, t=tmpl: self._apply_preset(t))
            preset_row.addWidget(btn)
        preset_row.addStretch()
        tmpl_layout.addLayout(preset_row)
        layout.addWidget(tmpl_group)

        # ── Selection toolbar
        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("Select:"))

        all_btn = QPushButton("☑ All")
        all_btn.setFixedHeight(26)
        all_btn.clicked.connect(lambda: self.model.set_all_checked(True))
        sel_row.addWidget(all_btn)

        none_btn = QPushButton("☐ None")
        none_btn.setFixedHeight(26)
        none_btn.clicked.connect(lambda: self.model.set_all_checked(False))
        sel_row.addWidget(none_btn)

        valid_btn = QPushButton("✅ Valid Only")
        valid_btn.setFixedHeight(26)
        valid_btn.clicked.connect(lambda: self.model.set_checked_by_status("valid"))
        sel_row.addWidget(valid_btn)

        shows_btn = QPushButton("📺 TV Shows")
        shows_btn.setFixedHeight(26)
        shows_btn.clicked.connect(lambda: self.model.set_checked_by_type("show"))
        sel_row.addWidget(shows_btn)

        movies_btn = QPushButton("🎬 Movies")
        movies_btn.setFixedHeight(26)
        movies_btn.clicked.connect(lambda: self.model.set_checked_by_type("movie"))
        sel_row.addWidget(movies_btn)

        sel_row.addStretch()
        layout.addLayout(sel_row)

        # ── Action buttons
        actions = QHBoxLayout()
        self.apply_btn = QPushButton("Apply Rename (Checked)")
        self.apply_btn.setObjectName("primary")
        self.apply_btn.clicked.connect(self.apply_changes)

        self.undo_btn = QPushButton("Undo Latest (20)")
        self.undo_btn.clicked.connect(self.undo_latest)

        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")

        actions.addWidget(self.apply_btn)
        actions.addWidget(self.undo_btn)
        actions.addStretch()
        actions.addWidget(self.status_label)
        layout.addLayout(actions)

        # ── Preview table
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # Fix column 0 (☑) to a narrow width
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 32)
        layout.addWidget(self.table)

        restore_column_widths(self.table, "rename")
        install_width_autosave(self.table, "rename")

    # ── Helpers

    def _load_template(self) -> None:
        saved = self.settings.get("rename_template", "{Title} ({Year}){Ext}")
        self.template_input.setText(saved)

    def _apply_preset(self, template: str) -> None:
        self.template_input.setText(template)
        self._preview_preserving_checks()

    def _update_status(self) -> None:
        rows = self.model.rows()
        if not rows:
            self.status_label.setText("")
            return
        checked  = len(self.model.checked_rows())
        valid    = sum(1 for r in rows if r["status"] == "valid")
        conflict = sum(1 for r in rows if r["status"] == "conflict")
        self.status_label.setText(
            f"{len(rows)} files — {valid} valid  {conflict} conflicts  —  {checked} selected"
        )

    # ── Actions

    def preview(self) -> None:
        template = self.template_input.text().strip()
        if not template:
            QMessageBox.warning(self, "Empty template", "Enter a rename template first.")
            return
        rows = self.rename_service.build_preview(template)
        self.model.set_rows(rows)
        self._update_status()

    def _preview_preserving_checks(self) -> None:
        """Re-run preview while keeping the user's current checkbox selections.

        Called by preset buttons so that manually-unchecked rows are not
        silently re-checked when the user switches to a different template.
        """
        template = self.template_input.text().strip()
        if not template:
            QMessageBox.warning(self, "Empty template", "Enter a rename template first.")
            return
        # Capture which old_paths are currently checked before re-building
        previously_checked = {
            r["old_path"]
            for r, c in zip(self.model.rows(), self.model._checked)
            if c
        }
        rows = self.rename_service.build_preview(template)
        # If the user had made no manual selections yet (first preview), auto-check valid rows
        if not previously_checked:
            self.model.set_rows(rows)
        else:
            self.model.set_rows(rows, preserve_paths=previously_checked)
        self._update_status()


    def clear_preview(self) -> None:
        self.model.set_rows([])
        self.status_label.setText("")

    def apply_changes(self) -> None:
        checked = self.model.checked_rows()
        rows = [r for r in checked if r["status"] == "valid"]
        skipped = len(checked) - len(rows)

        if not rows:
            QMessageBox.information(
                self, "Nothing to apply",
                "No checked rows with status 'valid'. "
                "Use the selection buttons or check rows manually."
            )
            return

        msg = f"Rename {len(rows)} selected file(s)?\nThis can be undone via the Undo button."
        if skipped:
            msg += f"\n\nNote: {skipped} checked row(s) with non-valid status will be skipped."

        reply = QMessageBox.question(
            self, "Apply Rename", msg,
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.apply_btn.setEnabled(False)
        self.worker = RenameWorker(rows)
        self.worker.finished_apply.connect(self.on_applied)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def on_applied(self, result: dict) -> None:
        self.apply_btn.setEnabled(True)
        QMessageBox.information(
            self, "Rename Complete",
            f'Success: {result["success"]}  Failed: {result["failed"]}',
        )
        self.preview()

    def on_failed(self, message: str) -> None:
        self.apply_btn.setEnabled(True)
        QMessageBox.critical(self, "Rename failed", message)

    def undo_latest(self) -> None:
        reply = QMessageBox.question(
            self, "Undo Renames",
            "Undo the last 20 rename operations?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        result = self.undo_service.undo_latest_renames(limit=20)
        QMessageBox.information(
            self, "Undo Complete",
            f'Undone: {result["undone"]}  Failed: {result["failed"]}',
        )
        self.preview()
