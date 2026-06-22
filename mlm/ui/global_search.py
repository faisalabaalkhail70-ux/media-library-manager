"""Global search bar widget — searches movies, shows, and episodes simultaneously.

Drop-in usage in MainWindow::

    from mlm.ui.global_search import GlobalSearchBar
    self._search_bar = GlobalSearchBar(self.stack, self.nav_buttons)
    outer.insertWidget(0, self._search_bar)   # insert above the main area
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QVBoxLayout, QLabel, QFrame
)
from PySide6.QtCore import Qt, QTimer
from mlm.db.connection import get_connection


class GlobalSearchBar(QWidget):
    """A top bar with a search input.  Results appear in a floating popup below it."""

    def __init__(self, stack, nav_buttons: list, parent=None) -> None:
        super().__init__(parent)
        self._stack = stack
        self._nav_buttons = nav_buttons
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(280)   # ms after last keystroke
        self._debounce.timeout.connect(self._run_search)

        bar_layout = QHBoxLayout(self)
        bar_layout.setContentsMargins(12, 4, 12, 4)

        self._input = QLineEdit()
        self._input.setPlaceholderText("\U0001f50d  Search movies, shows, episodes...")
        self._input.setFixedHeight(32)
        self._input.setMinimumWidth(400)
        self._input.textChanged.connect(self._on_text_changed)
        self._input.returnPressed.connect(self._run_search)

        bar_layout.addStretch()
        bar_layout.addWidget(self._input)
        bar_layout.addStretch()

        # Floating results popup — parented to the top-level window so it overlays content
        self._popup = _SearchPopup(self._input, stack, nav_buttons)

    def _on_text_changed(self, text: str) -> None:
        if not text.strip():
            self._popup.hide()
            return
        self._debounce.start()

    def _run_search(self) -> None:
        q = self._input.text().strip()
        if not q:
            self._popup.hide()
            return
        results = _do_search(q)
        self._popup.show_results(results)


class _SearchPopup(QFrame):
    """A frameless floating list that appears below the search input."""

    def __init__(self, anchor: QLineEdit, stack, nav_buttons: list) -> None:
        # Parent = None so it's a top-level frameless window that overlays everything
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._anchor = anchor
        self._stack = stack
        self._nav_buttons = nav_buttons
        self.setObjectName("stat_card")
        self.setFixedWidth(560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self._hint = QLabel("No results")
        self._hint.setObjectName("muted")
        layout.addWidget(self._hint)

        self._list = QListWidget()
        self._list.setFrameShape(QFrame.NoFrame)
        self._list.setMaximumHeight(340)
        self._list.itemActivated.connect(self._on_item_activated)
        layout.addWidget(self._list)

        # Map item data to view indices: movies=3, shows=4
        self._VIEW_INDEX = {"movie": 3, "show": 4, "episode": 4}

    def show_results(self, results: dict) -> None:
        self._list.clear()
        total = sum(len(v) for v in results.values())
        if total == 0:
            self._hint.setText("No results found")
            self._list.hide()
        else:
            self._hint.setText(f"{total} result(s) — press Enter or click to navigate")
            self._list.show()
            for group, items in results.items():
                if not items:
                    continue
                # Section header
                hdr = QListWidgetItem(f"  {group.upper()}S")
                hdr.setFlags(Qt.NoItemFlags)
                hdr.setForeground(Qt.gray)
                self._list.addItem(hdr)
                for item in items:
                    li = QListWidgetItem(f"    {item['title']}")
                    li.setData(Qt.UserRole, item)
                    self._list.addItem(li)

        # Position popup flush below the anchor
        pos = self._anchor.mapToGlobal(self._anchor.rect().bottomLeft())
        self.move(pos)
        self.show()
        self.raise_()

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.UserRole)
        if not data:
            return
        media_type = data.get("media_type", "movie")
        view_idx = self._VIEW_INDEX.get(media_type, 3)
        self._stack.setCurrentIndex(view_idx)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == view_idx)
        self.hide()
        self._anchor.clear()


def _do_search(q: str) -> dict:
    """Query movies, shows, and episodes for *q* and return grouped results."""
    like = f"%{q}%"
    with get_connection() as conn:
        movies = conn.execute(
            """
            SELECT id, title, release_year, 'movie' AS media_type
            FROM media_entities
            WHERE media_type = 'movie' AND title LIKE ?
            ORDER BY title LIMIT 8
            """,
            (like,),
        ).fetchall()

        shows = conn.execute(
            """
            SELECT id, title, release_year, 'show' AS media_type
            FROM media_entities
            WHERE media_type = 'show' AND title LIKE ?
            ORDER BY title LIMIT 8
            """,
            (like,),
        ).fetchall()

        episodes = conn.execute(
            """
            SELECT ep.id,
                   me.title || '  S' || printf('%02d', ep.season_number)
                             || 'E' || printf('%02d', ep.episode_number)
                             || CASE WHEN ep.episode_title != '' THEN '  — ' || ep.episode_title ELSE '' END
                   AS title,
                   me.release_year,
                   'episode' AS media_type
            FROM episodes ep
            JOIN media_entities me ON me.id = ep.entity_id
            WHERE (me.title LIKE ? OR ep.episode_title LIKE ?)
              AND ep.is_missing = 0
            ORDER BY me.title, ep.season_number, ep.episode_number
            LIMIT 8
            """,
            (like, like),
        ).fetchall()

    return {
        "movie":   [dict(r) for r in movies],
        "show":    [dict(r) for r in shows],
        "episode": [dict(r) for r in episodes],
    }
