"""Movies view — enriched with stats bar, open-folder, play-file,
CSV export, TMDB metadata refresh, and column-width persistence.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QTableView, QLineEdit, QAbstractItemView, QStackedWidget,
    QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QSortFilterProxyModel, QTimer

from mlm.db.connection import get_connection
from mlm.ui.models.movies_model import MoviesTableModel
from mlm.ui.column_visibility import (
    ColumnVisibilityDialog, apply_saved_visibility,
    restore_column_widths, install_width_autosave,
)
from mlm.ui.filter_panel import FilterPanel
from mlm.ui.grid_view import PosterGridWidget
from mlm.ui.views.entity_detail_panel import EntityDetailPanel


def _open_path(path: str) -> None:
    """Open a file with its default application.

    Shows a friendly QMessageBox with the path if the helper tool
    (xdg-open / open) is not found instead of crashing.
    """
    if not path or not os.path.exists(path):
        return
    try:
        if sys.platform == "win32":
            os.startfile(path)          # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path], stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["xdg-open", path], stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(None, "Open File", f"Could not open automatically:\n{path}")


def _open_folder(path: str) -> None:
    """Reveal the file in the OS file manager.

    On Linux, xdg-open only supports opening a folder (no file highlight),
    so we open the parent folder as a best-effort.  Falls back to showing
    the path in a dialog if the helper is not found.
    """
    if not path or not os.path.exists(path):
        return
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", path], stderr=subprocess.DEVNULL)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path], stderr=subprocess.DEVNULL)
        else:
            # xdg-open cannot highlight a file; open its folder instead
            subprocess.Popen(["xdg-open", os.path.dirname(path)], stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(None, "Open Folder", f"File is located at:\n{path}")


class MoviesView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._all_rows: list[dict] = []
        self._source_model = MoviesTableModel([])
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._source_model)
        self._proxy.setSortCaseSensitivity(Qt.CaseInsensitive)
        self._detail: EntityDetailPanel | None = None
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._apply_all_now)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        # ── Header row
        hdr_row = QHBoxLayout()
        title_lbl = QLabel("Movies")
        title_lbl.setObjectName("h1")
        hdr_row.addWidget(title_lbl)
        hdr_row.addStretch()
        self._stats_label = QLabel("")
        self._stats_label.setObjectName("muted")
        hdr_row.addWidget(self._stats_label)
        layout.addLayout(hdr_row)

        # ── Stats bar
        stats_frame = QFrame()
        stats_frame.setObjectName("stat_card")
        stats_row = QHBoxLayout(stats_frame)
        stats_row.setContentsMargins(12, 6, 12, 6)
        stats_row.setSpacing(32)
        self._lbl_count    = self._make_stat("Movies",        "0")
        self._lbl_size     = self._make_stat("Total Size",    "—")
        self._lbl_runtime  = self._make_stat("Total Runtime", "—")
        self._lbl_avg_rat  = self._make_stat("Avg Rating",    "—")
        self._lbl_hd       = self._make_stat("HD (1080p+)",   "0")
        for pair in (self._lbl_count, self._lbl_size, self._lbl_runtime,
                     self._lbl_avg_rat, self._lbl_hd):
            stats_row.addWidget(pair[0])  # value label
            stats_row.addWidget(pair[1])  # caption label
            if pair is not self._lbl_hd:
                sep = QFrame()
                sep.setFrameShape(QFrame.VLine)
                sep.setStyleSheet("color: #3a3a4a;")
                stats_row.addWidget(sep)
        stats_row.addStretch()
        layout.addWidget(stats_frame)

        # ── Toolbar
        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by title...")
        self.search_input.setFixedWidth(280)
        self.search_input.textChanged.connect(self._search_timer.start)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.search_input.clear)

        # Action buttons
        self._open_btn   = QPushButton("▶ Play")
        self._open_btn.setToolTip("Open selected file with default player")
        self._open_btn.clicked.connect(self._play_selected)

        self._folder_btn = QPushButton("📂 Folder")
        self._folder_btn.setToolTip("Show file in Explorer")
        self._folder_btn.clicked.connect(self._open_folder_selected)

        self._export_btn = QPushButton("↧ Export CSV")
        self._export_btn.clicked.connect(self._export_csv)

        self._refresh_btn = QPushButton("🔄 Refresh Metadata")
        self._refresh_btn.setToolTip("Re-fetch TMDB metadata for selected movie")
        self._refresh_btn.clicked.connect(self._refresh_metadata)

        col_btn = QPushButton("\u2699 Columns")
        col_btn.clicked.connect(self._open_col_dialog)

        refresh_data_btn = QPushButton("Refresh")
        refresh_data_btn.clicked.connect(self.load_rows)

        self._view_toggle = QPushButton("\u22f9 Grid View")
        self._view_toggle.setCheckable(True)
        self._view_toggle.clicked.connect(self._toggle_view)

        toolbar.addWidget(self.search_input)
        toolbar.addWidget(clear_btn)
        toolbar.addSpacing(8)
        toolbar.addWidget(self._open_btn)
        toolbar.addWidget(self._folder_btn)
        toolbar.addWidget(self._refresh_btn)
        toolbar.addWidget(self._export_btn)
        toolbar.addStretch()
        toolbar.addWidget(self._view_toggle)
        toolbar.addWidget(col_btn)
        toolbar.addWidget(refresh_data_btn)
        layout.addLayout(toolbar)

        # ── Filter panel
        self._filters = FilterPanel(media_type="movie")
        self._filters.changed.connect(self._apply_all)
        layout.addWidget(self._filters)

        # ── Stacked: table | grid
        self._stack = QStackedWidget()

        self.table = QTableView()
        self.table.setModel(self._proxy)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.doubleClicked.connect(self._open_detail_from_table)
        self._stack.addWidget(self.table)

        self._grid = PosterGridWidget()
        self._grid.card_clicked.connect(self._open_detail)
        self._stack.addWidget(self._grid)

        layout.addWidget(self._stack)

        self.load_rows()
        apply_saved_visibility(self.table, "movies")
        restore_column_widths(self.table, "movies")
        install_width_autosave(self.table, "movies")

    # ── Stat widget helper

    def _make_stat(self, caption: str, initial: str) -> tuple[QLabel, QLabel]:
        """Returns (value_label, caption_label) pair for the stats bar."""
        val = QLabel(initial)
        val.setStyleSheet("font-size: 16px; font-weight: bold; color: #d0d0e8;")
        cap = QLabel(caption)
        cap.setStyleSheet("font-size: 10px; color: #6e6e8a; margin-bottom: 2px;")
        cap.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        return (val, cap)

    def _update_stats(self, rows: list[dict]) -> None:
        count    = len(rows)
        total_b  = sum(r.get("file_size_bytes") or 0 for r in rows)
        ratings  = [float(r["rating"]) for r in rows if r.get("rating")]
        avg_rat  = sum(ratings) / len(ratings) if ratings else None
        hd_count = sum(
            1 for r in rows
            if self._res_width(r.get("resolution")) >= 1920
        )

        # Total runtime from the currently visible (filtered) rows
        total_secs = sum(r.get("duration_seconds") or 0 for r in rows)
        h = total_secs // 3600
        m = (total_secs % 3600) // 60

        # Size
        if total_b >= 1024 ** 4:
            size_str = f"{total_b / 1024**4:.1f} TB"
        elif total_b >= 1024 ** 3:
            size_str = f"{total_b / 1024**3:.1f} GB"
        else:
            size_str = f"{total_b / 1024**2:.0f} MB"

        self._lbl_count[0].setText(str(count))
        self._lbl_size[0].setText(size_str)
        self._lbl_runtime[0].setText(f"{h}h {m:02d}m" if total_secs else "—")
        self._lbl_avg_rat[0].setText(f"{avg_rat:.1f}" if avg_rat else "—")
        self._lbl_hd[0].setText(str(hd_count))

    @staticmethod
    def _res_width(res: str | None) -> int:
        if not res:
            return 0
        part = res.split("x")[0] if "x" in res else res.lower().replace("p", "")
        try:
            return int(part)
        except ValueError:
            return 0

    # ── Data

    def load_rows(self) -> None:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT me.id AS entity_id, me.title, me.release_year,
                       me.rating, me.genres_json, me.poster_path,
                       mf.resolution, mf.file_size_bytes, mf.file_name,
                       mf.file_path, mf.duration_seconds
                FROM media_entities me
                LEFT JOIN media_files mf ON mf.entity_id = me.id AND mf.removed_at IS NULL
                WHERE me.media_type = 'movie'
                ORDER BY me.title ASC
                """
            ).fetchall()

        result = []
        for r in rows:
            d = dict(r)
            try:
                genres = json.loads(d.get("genres_json") or "[]")
                d["genres"] = ", ".join(g.get("name", "") for g in genres)
            except Exception:
                d["genres"] = ""
            result.append(d)

        self._all_rows = result
        self._filters.populate_genres(result)
        self._apply_all()

    def _apply_all(self) -> None:
        """Called by filter panel signal (immediate) or programmatically."""
        self._apply_all_now()

    def _apply_all_now(self) -> None:
        q = self.search_input.text().strip().lower()
        rows = self._all_rows
        if q:
            rows = [r for r in rows if q in r.get("title", "").lower()]
        rows = self._filters.apply(rows)
        self._source_model.set_rows(rows)
        self._grid.set_rows(rows)
        self._stats_label.setText(f"{len(rows)} of {len(self._all_rows)} movies")
        self._update_stats(rows)

    # ── View toggle

    def _toggle_view(self) -> None:
        is_grid = self._view_toggle.isChecked()
        self._stack.setCurrentIndex(1 if is_grid else 0)
        self._view_toggle.setText("\u2630 List View" if is_grid else "\u22f9 Grid View")

    # ── Detail

    def _open_detail(self, entity_id: int) -> None:
        self._detail = EntityDetailPanel(entity_id, parent=self)
        self._detail.show()

    def _open_detail_from_table(self, index) -> None:
        src = self._proxy.mapToSource(index)
        row = self._source_model._rows[src.row()]
        self._open_detail(row.get("entity_id"))

    # ── Selected row helper

    def _selected_row(self) -> dict | None:
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return None
        src = self._proxy.mapToSource(sel[0])
        return self._source_model._rows[src.row()]

    # ── Actions

    def _play_selected(self) -> None:
        row = self._selected_row()
        if not row:
            QMessageBox.information(self, "No selection", "Select a movie first.")
            return
        path = row.get("file_path") or ""
        if not os.path.exists(path):
            QMessageBox.warning(self, "File not found", f"Cannot find:\n{path}")
            return
        _open_path(path)

    def _open_folder_selected(self) -> None:
        row = self._selected_row()
        if not row:
            QMessageBox.information(self, "No selection", "Select a movie first.")
            return
        path = row.get("file_path") or ""
        _open_folder(path)

    def _refresh_metadata(self) -> None:
        row = self._selected_row()
        if not row:
            QMessageBox.information(self, "No selection", "Select a movie first.")
            return
        entity_id = row.get("entity_id")
        title     = row.get("title", "?")
        reply = QMessageBox.question(
            self, "Refresh Metadata",
            f'Re-fetch TMDB metadata for "{title}"?',
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            from mlm.services.metadata_service import MetadataService
            svc = MetadataService()
            svc.refresh_entity(entity_id)
            self.load_rows()
            QMessageBox.information(self, "Done", f'"{title}" metadata refreshed.')
        except ValueError as exc:
            # Entity has no TMDB id — tell user they need to match first
            QMessageBox.warning(self, "Cannot Refresh", str(exc))
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Refresh failed:\n{exc}")


    def _export_csv(self) -> None:
        rows = self._source_model._rows
        if not rows:
            QMessageBox.information(self, "Empty", "No movies to export.")
            return
        from mlm.app.paths import EXPORT_DIR
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = EXPORT_DIR / f"movies_{ts}.csv"
        fields = ["title", "release_year", "rating", "genres", "resolution",
                  "file_size_bytes", "file_name", "file_path"]
        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        QMessageBox.information(self, "Exported", f"Saved {len(rows)} rows to:\n{out}")

    def _open_col_dialog(self) -> None:
        dlg = ColumnVisibilityDialog(self.table, "movies", parent=self)
        dlg.exec()
