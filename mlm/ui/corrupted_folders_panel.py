"""CorruptedFoldersPanel — a self-contained collapsible panel that lists every
parent folder containing corrupted media files.

Usage (inside HealthView or any QVBoxLayout):

    panel = CorruptedFoldersPanel()
    layout.addWidget(panel)
    panel.reload()          # call after every health scan

Signals
    folder_count_changed(int)  — emits the number of affected folders whenever
                                  reload() finishes. Lets the caller update a
                                  sidebar badge or status label.
"""
from __future__ import annotations
import os

from PySide6.QtCore  import Qt, QSize, Signal
from PySide6.QtGui   import QColor, QPainter, QLinearGradient, QPen, QPainterPath, QFont, QFontMetrics, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QSizePolicy, QPushButton,
    QApplication,
)

from mlm.services.corrupted_folders_service import CorruptedFoldersService
from mlm.ui.widgets import GlassCard, SectionHeader, BadgeLabel


# ──────────────────────────────────────────────────────────────────────
class _FolderRow(QWidget):
    """
    One affected-folder row. Draws a GlassCard with:
      ─ Left: media-type badge  +  title  +  full path
      ─ Right: red corrupted-count pill  +  copy-path button
    """
    def __init__(
        self,
        title:           str,
        media_type:      str | None,
        folder_path:     str,
        corrupted_count: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setFixedHeight(72)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Outer glass card (red accent bar = danger signal)
        card = GlassCard(
            self,
            radius=12,
            accent=QColor(239, 83, 80),
            accent_h=3,
            hover_glow=True,
        )
        card.setGeometry(0, 0, 9999, 72)   # stretched by resizeEvent

        outer = QHBoxLayout(card)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(12)

        # ─ Left column
        left = QVBoxLayout()
        left.setSpacing(2)

        # Row 1: type badge + title
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        top_row.setContentsMargins(0, 0, 0, 0)

        # Media type badge
        badge_text = "MOVIE" if media_type == "movie" else "TV SHOW" if media_type == "show" else "MEDIA"
        badge_bg   = (
            QColor(66, 165, 245, 40)  if media_type == "movie"
            else QColor(102, 187, 106, 40) if media_type == "show"
            else QColor(120, 120, 120, 40)
        )
        badge_fg = (
            QColor(100, 185, 255) if media_type == "movie"
            else QColor(130, 210, 130) if media_type == "show"
            else QColor(170, 170, 170)
        )
        type_badge = BadgeLabel(badge_text, bg=badge_bg, fg=badge_fg)
        top_row.addWidget(type_badge, 0, Qt.AlignVCenter)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "color: #dddaff; font-size: 13px; font-weight: 700; background: transparent;"
        )
        title_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        top_row.addWidget(title_lbl, 1)
        left.addLayout(top_row)

        # Row 2: folder path
        path_lbl = QLabel(folder_path)
        path_lbl.setStyleSheet(
            "color: #50507a; font-size: 10px; font-family: 'Cascadia Code', 'Consolas', monospace;"
            "background: transparent;"
        )
        path_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        left.addWidget(path_lbl)

        outer.addLayout(left, 1)

        # ─ Right column
        right = QVBoxLayout()
        right.setSpacing(6)
        right.setAlignment(Qt.AlignVCenter | Qt.AlignRight)

        # Corrupted count pill
        count_lbl = QLabel(str(corrupted_count))
        count_lbl.setAlignment(Qt.AlignCenter)
        count_lbl.setFixedWidth(42)
        count_lbl.setFixedHeight(26)
        count_lbl.setStyleSheet(
            "color: #ff6b6b; font-size: 15px; font-weight: 800;"
            "background: rgba(239,83,80,18); border: 1px solid rgba(239,83,80,60);"
            "border-radius: 6px;"
        )
        right.addWidget(count_lbl, 0, Qt.AlignRight)

        # Copy path button
        copy_btn = QPushButton("⧅ Copy")
        copy_btn.setFixedHeight(22)
        copy_btn.setFixedWidth(62)
        copy_btn.setStyleSheet(
            "color: #6060a0; font-size: 9px; background: transparent;"
            "border: 1px solid rgba(100,100,160,40); border-radius: 4px;"
            "padding: 0 6px;"
        )
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(folder_path))
        right.addWidget(copy_btn, 0, Qt.AlignRight)

        outer.addLayout(right)
        self._card = card

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._card.setGeometry(0, 0, self.width(), self.height())


# ──────────────────────────────────────────────────────────────────────
class CorruptedFoldersPanel(QWidget):
    """
    Collapsible panel that shows all folders containing corrupted files.

    Header bar (always visible):
      [⚠ Corrupted Folders]  [12 folders • 47 files]  [ ▼ collapse ]

    Body (collapsible):
      Scrollable list of _FolderRow cards
    """
    folder_count_changed = Signal(int)   # emits affected-folder count

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._service   = CorruptedFoldersService()
        self._collapsed = False
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header bar (always visible)
        self._header = self._build_header()
        root.addWidget(self._header)

        # ── Body: scroll area containing folder rows
        self._body = QWidget()
        self._body.setStyleSheet("background: transparent;")
        self._body_lay = QVBoxLayout(self._body)
        self._body_lay.setContentsMargins(0, 6, 0, 0)
        self._body_lay.setSpacing(6)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")
        self._scroll.setMaximumHeight(340)
        self._scroll.setWidget(self._body)
        root.addWidget(self._scroll)

        self.reload()

    # ── Internal builders───────────────────────────────────────────────────

    def _build_header(self) -> QWidget:
        hdr = QWidget()
        hdr.setFixedHeight(48)
        hdr.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        self._section_hdr = SectionHeader(
            "⚠  Corrupted Folders",
            "Folders containing files flagged as errors by the health scan",
            QColor(239, 83, 80),
        )
        self._section_hdr.setFixedHeight(48)
        lay.addWidget(self._section_hdr, 1)

        self._summary_lbl = QLabel("")
        self._summary_lbl.setStyleSheet(
            "color: #ef5350; font-size: 11px; font-weight: 600; background: transparent;"
        )
        lay.addWidget(self._summary_lbl, 0, Qt.AlignVCenter)

        self._toggle_btn = QPushButton("▼")
        self._toggle_btn.setFixedSize(28, 28)
        self._toggle_btn.setStyleSheet(
            "color: #60607a; background: transparent; border: none; font-size: 10px;"
        )
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle_collapse)
        lay.addWidget(self._toggle_btn)

        return hdr

    # ── Public API─────────────────────────────────────────────────────────

    def reload(self) -> None:
        """Fetch fresh data from the DB and rebuild the folder rows."""
        # Clear existing rows
        while self._body_lay.count():
            item = self._body_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        folders = self._service.corrupted_folders()
        total_files = sum(f["corrupted_count"] for f in folders)
        n_folders   = len(folders)

        if n_folders == 0:
            empty = QLabel("✅  No corrupted folders detected — all files healthy.")
            empty.setStyleSheet(
                "color: #50a060; font-size: 12px; padding: 12px 4px; background: transparent;"
            )
            self._body_lay.addWidget(empty)
            self._summary_lbl.setText("")
        else:
            for f in folders:
                row = _FolderRow(
                    title=f["title"],
                    media_type=f["media_type"],
                    folder_path=f["folder_path"],
                    corrupted_count=f["corrupted_count"],
                )
                self._body_lay.addWidget(row)
            self._body_lay.addStretch()

            plural_f = "folder" if n_folders == 1 else "folders"
            plural_c = "file"   if total_files == 1 else "files"
            self._summary_lbl.setText(
                f"{n_folders} {plural_f}  •  {total_files} corrupted {plural_c}"
            )

        self.folder_count_changed.emit(n_folders)

    # ── Collapse toggle─────────────────────────────────────────────────────

    def _toggle_collapse(self) -> None:
        self._collapsed = not self._collapsed
        self._scroll.setVisible(not self._collapsed)
        self._toggle_btn.setText("▶" if self._collapsed else "▼")
