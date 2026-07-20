"""Sprint 7: scrollable list of ResultCard widgets, replacing the old
QTableWidget results display. MainWindow calls set_results(hits, theme) with
whatever DatabaseSearchEngine already returned -- this widget has no search
logic of its own, only presentation."""

from PySide6.QtCore import QPropertyAnimation, Qt, Signal
from PySide6.QtWidgets import QGraphicsOpacityEffect, QScrollArea, QVBoxLayout, QWidget

from memoryos.search.engine import SearchHit
from memoryos.theme import Theme
from memoryos.ui.result_card import ResultCard

_FADE_DURATION_MS = 180


class ResultsView(QWidget):
    open_requested = Signal(str)
    reveal_requested = Signal(str)
    copy_requested = Signal(str)
    rename_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = Theme.LIGHT
        self._cards: list[ResultCard] = []
        self._fade_animation: QPropertyAnimation | None = None

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(8)
        self._container_layout.addStretch(1)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setWidget(self._container)
        outer_layout.addWidget(scroll_area)

    def set_results(self, hits: list[SearchHit], theme: Theme) -> None:
        self._theme = theme
        for card in self._cards:
            card.setParent(None)
        self._cards.clear()

        for hit in hits:
            card = ResultCard(hit, theme)
            card.open_requested.connect(self.open_requested)
            card.reveal_requested.connect(self.reveal_requested)
            card.copy_requested.connect(self.copy_requested)
            card.rename_requested.connect(self.rename_requested)
            card.delete_requested.connect(self.delete_requested)
            self._container_layout.insertWidget(self._container_layout.count() - 1, card)
            self._cards.append(card)

        self._play_fade_in()

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        for card in self._cards:
            card.set_theme(theme)

    def _play_fade_in(self) -> None:
        effect = QGraphicsOpacityEffect(self._container)
        self._container.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(_FADE_DURATION_MS)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        # Clear the effect once fully opaque -- leaving a QGraphicsOpacityEffect
        # attached permanently forces Qt to render this subtree through an
        # offscreen buffer on every repaint, even once opacity is back to 1.0.
        animation.finished.connect(lambda: self._container.setGraphicsEffect(None))
        animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._fade_animation = animation
