"""MetadataEditorDialog — floating editor for a single media entity.

Opened from LibraryView, MoviesView, ShowsView, and EntityDetailPanel
by calling::

    dlg = MetadataEditorDialog(entity_id=42, media_file_id=7, parent=self)
    dlg.exec()

If *entity_id* is None (unmatched file), the dialog opens in
"search-only" mode so the user can find and link an entity.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox,
    QSplitter, QWidget, QProgressBar, QGroupBox,
    QSpinBox, QDoubleSpinBox, QScrollArea, QFrame,
)

from mlm.services.metadata_editor_service import MetadataEditorService

log = logging.getLogger(__name__)


# ── Background workers ────────────────────────────────────────────────

class _SearchWorker(QThread):
    results_ready = Signal(list)
    failed = Signal(str)

    def __init__(self, svc: MetadataEditorService, query: str, media_type: str, year: int | None):
        super().__init__()
        self._svc = svc
        self._query = query
        self._media_type = media_type
        self._year = year

    def run(self):
        try:
            results = self._svc.search_tmdb(self._query, self._media_type, self._year)
            self.results_ready.emit(results)
        except Exception as exc:
            self.failed.emit(str(exc))


class _ApplyWorker(QThread):
    done = Signal()
    failed = Signal(str)

    def __init__(self, svc: MetadataEditorService, entity_id: int, tmdb_id: int, media_type: str):
        super().__init__()
        self._svc = svc
        self._entity_id = entity_id
        self._tmdb_id = tmdb_id
        self._media_type = media_type

    def run(self):
        try:
            self._svc.apply_tmdb_pick(self._entity_id, self._tmdb_id, self._media_type)
            self.done.emit()
        except Exception as exc:
            self.failed.emit(str(exc))


# ── Main dialog ───────────────────────────────────────────────────────

class MetadataEditorDialog(QDialog):
    """Two-panel dialog: left = edit fields, right = TMDB re-search."""

    metadata_saved = Signal()  # emit after any successful save

    def __init__(
        self,
        entity_id: int | None = None,
        media_file_id: int | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Metadata")
        self.setMinimumSize(860, 580)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self._svc = MetadataEditorService()
        self._entity_id = entity_id
        self._media_file_id = media_file_id
        self._entity: dict | None = None
        self._search_worker: _SearchWorker | None = None
        self._apply_worker: _ApplyWorker | None = None
        self._tmdb_results: list[dict] = []

        # Load entity
        if entity_id:
            self._entity = self._svc.get_entity(entity_id)
        elif media_file_id:
            self._entity = self._svc.get_entity_for_file(media_file_id)
            if self._entity:
                self._entity_id = self._entity["id"]

        self._build_ui()
        if self._entity:
            self._populate_fields(self._entity)

    # ── UI construction ───────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(10)

        # Title row
        title_lbl = QLabel("Edit Metadata")
        title_lbl.setObjectName("h1")
        lock_note = QLabel("Fields you save will be locked from future auto-matching.")
        lock_note.setObjectName("muted")
        root.addWidget(title_lbl)
        root.addWidget(lock_note)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(6)
        root.addWidget(splitter, 1)

        # ── LEFT: manual edit form ─────────────────────────────────
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 8, 0)
        left_lay.setSpacing(8)

        form_group = QGroupBox("Manual Fields")
        form = QFormLayout(form_group)
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)

        self._title_edit = QLineEdit()
        self._year_spin  = QSpinBox()
        self._year_spin.setRange(1888, 2100)
        self._year_spin.setSpecialValueText("Unknown")
        self._year_spin.setValue(0)
        self._rating_spin = QDoubleSpinBox()
        self._rating_spin.setRange(0.0, 10.0)
        self._rating_spin.setSingleStep(0.1)
        self._rating_spin.setDecimals(1)
        self._genres_edit = QLineEdit()
        self._genres_edit.setPlaceholderText("Action, Drama, Sci-Fi  (comma-separated)")
        self._plot_edit = QTextEdit()
        self._plot_edit.setFixedHeight(90)
        self._poster_edit = QLineEdit()
        self._poster_edit.setPlaceholderText("/path/to/poster.jpg  or TMDB path")

        form.addRow("Title:", self._title_edit)
        form.addRow("Year:", self._year_spin)
        form.addRow("Rating:", self._rating_spin)
        form.addRow("Genres:", self._genres_edit)
        form.addRow("Plot:", self._plot_edit)
        form.addRow("Poster path:", self._poster_edit)
        left_lay.addWidget(form_group)

        self._save_manual_btn = QPushButton("💾  Save Manual Override")
        self._save_manual_btn.setObjectName("primary")
        self._save_manual_btn.clicked.connect(self._save_manual)
        left_lay.addWidget(self._save_manual_btn)
        left_lay.addStretch()

        splitter.addWidget(left)

        # ── RIGHT: TMDB re-search ──────────────────────────────────
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(8, 0, 0, 0)
        right_lay.setSpacing(6)

        search_group = QGroupBox("Search TMDB")
        sg_lay = QVBoxLayout(search_group)
        sg_lay.setSpacing(6)

        search_row = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Title to search on TMDB...")
        self._search_input.returnPressed.connect(self._run_search)
        self._search_btn = QPushButton("Search")
        self._search_btn.clicked.connect(self._run_search)
        search_row.addWidget(self._search_input, 1)
        search_row.addWidget(self._search_btn)
        sg_lay.addLayout(search_row)

        self._search_progress = QProgressBar()
        self._search_progress.setRange(0, 0)
        self._search_progress.setFixedHeight(4)
        self._search_progress.setVisible(False)
        sg_lay.addWidget(self._search_progress)

        self._results_list = QListWidget()
        self._results_list.setAlternatingRowColors(True)
        self._results_list.setMinimumHeight(280)
        self._results_list.itemDoubleClicked.connect(self._apply_tmdb_pick)
        sg_lay.addWidget(self._results_list)

        self._result_hint = QLabel("Double-click a result to apply it.")
        self._result_hint.setObjectName("muted")
        sg_lay.addWidget(self._result_hint)

        right_lay.addWidget(search_group)

        self._apply_btn = QPushButton("✅  Apply Selected TMDB Result")
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._apply_tmdb_pick)
        right_lay.addWidget(self._apply_btn)
        right_lay.addStretch()

        splitter.addWidget(right)
        splitter.setSizes([420, 420])

        # ── Bottom bar ─────────────────────────────────────────────
        bottom = QHBoxLayout()
        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("muted")
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(self._status_lbl, 1)
        bottom.addWidget(close_btn)
        root.addLayout(bottom)

    # ── Populate ──────────────────────────────────────────────────────

    def _populate_fields(self, entity: dict):
        self._title_edit.setText(entity.get("title") or "")
        year = entity.get("release_year")
        if year:
            self._year_spin.setValue(int(year))
        rating = entity.get("rating")
        if rating:
            self._rating_spin.setValue(float(rating))
        # Genres stored as JSON list
        import json
        genres_raw = entity.get("genres_json") or "[]"
        try:
            genres = json.loads(genres_raw)
            self._genres_edit.setText(", ".join(genres))
        except Exception:
            self._genres_edit.setText(genres_raw)
        self._plot_edit.setPlainText(entity.get("plot") or "")
        self._poster_edit.setText(entity.get("poster_path") or "")
        # Pre-fill search box with current title
        self._search_input.setText(entity.get("title") or "")

    # ── Manual save ───────────────────────────────────────────────────

    def _save_manual(self):
        if not self._entity_id:
            QMessageBox.warning(self, "No Entity", "No media entity is linked to this file.")
            return
        import json
        genres_text = self._genres_edit.text().strip()
        genres_list = [g.strip() for g in genres_text.split(",") if g.strip()]
        fields = {
            "title":        self._title_edit.text().strip(),
            "release_year": self._year_spin.value() or None,
            "rating":       self._rating_spin.value(),
            "genres_json":  json.dumps(genres_list),
            "plot":         self._plot_edit.toPlainText().strip(),
            "poster_path":  self._poster_edit.text().strip(),
        }
        try:
            self._svc.save_manual_override(self._entity_id, fields)
            self._status_lbl.setText("✅  Saved. This entity is now locked from auto-matching.")
            self.metadata_saved.emit()
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))

    # ── TMDB search ───────────────────────────────────────────────────

    def _run_search(self):
        query = self._search_input.text().strip()
        if not query:
            return
        media_type = self._entity.get("media_type", "movie") if self._entity else "movie"
        year = self._entity.get("release_year") if self._entity else None
        self._search_progress.setVisible(True)
        self._search_btn.setEnabled(False)
        self._results_list.clear()
        self._apply_btn.setEnabled(False)
        self._tmdb_results = []

        self._search_worker = _SearchWorker(self._svc, query, media_type, year)
        self._search_worker.results_ready.connect(self._on_results)
        self._search_worker.failed.connect(self._on_search_failed)
        self._search_worker.start()

    def _on_results(self, results: list[dict]):
        self._search_progress.setVisible(False)
        self._search_btn.setEnabled(True)
        self._tmdb_results = results
        self._results_list.clear()
        if not results:
            self._result_hint.setText("No results found on TMDB.")
            return
        for r in results:
            year_str = f" ({r['release_year']})" if r.get("release_year") else ""
            rating_str = f"  ⭐ {r['vote_average']:.1f}" if r.get("vote_average") else ""
            label = f"{r['title']}{year_str}{rating_str}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, r)
            self._results_list.addItem(item)
        self._result_hint.setText(f"{len(results)} result(s) — double-click to apply.")
        self._apply_btn.setEnabled(True)

    def _on_search_failed(self, msg: str):
        self._search_progress.setVisible(False)
        self._search_btn.setEnabled(True)
        self._result_hint.setText(f"Search failed: {msg}")

    def _apply_tmdb_pick(self, item: QListWidgetItem | None = None):
        if item is None:
            selected = self._results_list.currentItem()
        else:
            selected = item
        if not selected:
            return
        data: dict = selected.data(Qt.UserRole)
        if not data or not self._entity_id:
            return
        media_type = self._entity.get("media_type", "movie") if self._entity else "movie"
        self._apply_btn.setEnabled(False)
        self._status_lbl.setText("Fetching full details from TMDB…")

        self._apply_worker = _ApplyWorker(
            self._svc, self._entity_id, data["tmdb_id"], media_type
        )
        self._apply_worker.done.connect(self._on_apply_done)
        self._apply_worker.failed.connect(self._on_apply_failed)
        self._apply_worker.start()

    def _on_apply_done(self):
        self._apply_btn.setEnabled(True)
        self._status_lbl.setText("✅  TMDB data applied and locked.")
        # Reload fields from DB
        if self._entity_id:
            self._entity = self._svc.get_entity(self._entity_id)
            if self._entity:
                self._populate_fields(self._entity)
        self.metadata_saved.emit()

    def _on_apply_failed(self, msg: str):
        self._apply_btn.setEnabled(True)
        QMessageBox.critical(self, "Apply Failed", f"Could not apply TMDB data:\n{msg}")
        self._status_lbl.setText("")
