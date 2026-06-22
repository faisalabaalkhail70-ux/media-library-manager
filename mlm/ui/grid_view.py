"""Reusable poster grid widget.

Usage::

    grid = PosterGridWidget()
    grid.set_rows(rows)           # list of entity dicts
    grid.card_clicked.connect(on_card_clicked)
"""
from PySide6.QtWidgets import (
    QWidget, QScrollArea, QFrame, QVBoxLayout
)
from PySide6.QtCore import Signal, Qt
from mlm.ui.poster_card import PosterCard

_CARD_W   = 148   # must match poster_card.py
_CARD_GAP = 12


class _FlowWidget(QWidget):
    """Widget that lays out children in a left-to-right wrapping flow."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cards: list[PosterCard] = []

    def set_cards(self, cards: list[PosterCard]) -> None:
        # Remove old cards
        for c in self._cards:
            c.setParent(None)
            c.deleteLater()
        self._cards = cards
        for c in cards:
            c.setParent(self)
        self._relayout()

    def _relayout(self) -> None:
        if not self._cards:
            self.setMinimumHeight(0)
            return
        w = self.width() or 800
        cols = max(1, (w + _CARD_GAP) // (_CARD_W + _CARD_GAP))
        x = y = _CARD_GAP
        for i, card in enumerate(self._cards):
            card.move(x, y)
            card.show()
            col = i % cols
            if col == cols - 1:
                x  = _CARD_GAP
                y += card.height() + _CARD_GAP
            else:
                x += _CARD_W + _CARD_GAP
        rows = (len(self._cards) + cols - 1) // cols
        self.setMinimumHeight(rows * (self._cards[0].height() + _CARD_GAP) + _CARD_GAP)

    def resizeEvent(self, event) -> None:
        self._relayout()
        super().resizeEvent(event)


class PosterGridWidget(QWidget):
    card_clicked = Signal(int)   # entity_id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        layout.addWidget(scroll)

        self._flow = _FlowWidget()
        scroll.setWidget(self._flow)

    def set_rows(self, rows: list[dict]) -> None:
        cards: list[PosterCard] = []
        for row in rows:
            card = PosterCard(row)
            card.clicked.connect(self.card_clicked)
            cards.append(card)
        self._flow.set_cards(cards)
