"""V2: a premium tab-style filter bar shown above ResultsView's results list
once a search actually has results. UI + placeholder signal only -- no real
filtering logic yet; see the widget's filter_selected signal, which a future
sprint can connect to without touching this file again."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QWidget

TAB_LABELS = ["All", "Images", "Web", "Files", "Notes", "More..."]


class SearchResultsFilterBar(QWidget):
    filter_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("filterBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(8)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}

        for label in TAB_LABELS:
            button = QPushButton(label)
            button.setObjectName("filterTab")
            button.setCheckable(True)
            button.clicked.connect(lambda checked, l=label: self._on_tab_clicked(l))
            self._button_group.addButton(button)
            self._buttons[label] = button
            layout.addWidget(button)

        layout.addStretch(1)
        self._buttons["All"].setChecked(True)

    def _on_tab_clicked(self, label: str) -> None:
        print(f"Filtering for: {label}")
        self.filter_selected.emit(label)

    def reset(self) -> None:
        self._buttons["All"].setChecked(True)
