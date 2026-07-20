"""Sprint 7: one card per search result, replacing a QTableWidget row.
Renders a SearchHit and exposes signals for the same five file actions
Sprint 4 already implemented -- MainWindow connects these to its existing,
unchanged handler methods; this widget knows nothing about Database or
file_actions itself."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from memoryos.search.engine import SearchHit
from memoryos.theme import Theme
from memoryos.ui.icons import get_icon

_PATH_ELIDE_MAX_CHARS = 90


class ResultCard(QWidget):
    open_requested = Signal(str)
    reveal_requested = Signal(str)
    copy_requested = Signal(str)
    rename_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, hit: SearchHit, theme: Theme, parent=None):
        super().__init__(parent)
        self.setObjectName("resultCard")
        # Plain QWidget subclasses don't paint QSS background-color/border by
        # default (unlike a bare QWidget() instance) -- this opts back in.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._path = hit.path
        self._build_ui(hit)
        self.set_theme(theme)

        # Sprint 7: right-click stays a secondary path to the same five
        # actions the inline icon buttons already expose (Sprint 4's context
        # menu, preserved rather than dropped now that rows are cards).
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _build_ui(self, hit: SearchHit) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        header_row = QHBoxLayout()
        self.filename_label = QLabel(hit.filename)
        self.filename_label.setStyleSheet("font-weight: 600; font-size: 13px;")
        similarity_label = QLabel(f"{hit.similarity:.0%} match")
        similarity_label.setObjectName("mutedLabel")
        header_row.addWidget(self.filename_label, 1)
        header_row.addWidget(similarity_label)
        layout.addLayout(header_row)

        path_label = QLabel(self._elided_path(hit.path))
        path_label.setObjectName("mutedLabel")
        path_label.setToolTip(hit.path)
        layout.addWidget(path_label)

        if hit.reasons:
            reasons_label = QLabel(" | ".join(hit.reasons))
            reasons_label.setObjectName("mutedLabel")
            reasons_label.setWordWrap(True)
            layout.addWidget(reasons_label)

        actions_row = QHBoxLayout()
        actions_row.addStretch(1)
        self._open_button = self._make_icon_button("open", "Open", self.open_requested)
        self._reveal_button = self._make_icon_button(
            "folder_open", "Reveal in Folder", self.reveal_requested
        )
        self._copy_button = self._make_icon_button("copy", "Copy Path", self.copy_requested)
        self._rename_button = self._make_icon_button("edit", "Rename...", self.rename_requested)
        self._delete_button = self._make_icon_button(
            "delete", "Delete", self.delete_requested, danger=True
        )
        for button in (
            self._open_button,
            self._reveal_button,
            self._copy_button,
            self._rename_button,
            self._delete_button,
        ):
            actions_row.addWidget(button)
        layout.addLayout(actions_row)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _make_icon_button(self, icon_name: str, tooltip: str, signal: Signal, danger: bool = False) -> QPushButton:
        button = QPushButton()
        button.setObjectName("dangerIconButton" if danger else "iconButton")
        button.setToolTip(tooltip)
        button.setProperty("iconName", icon_name)
        button.clicked.connect(lambda: signal.emit(self._path))
        return button

    def _elided_path(self, path: str) -> str:
        metrics = QFontMetrics(self.font())
        avg_char_width = metrics.averageCharWidth() or 6
        return metrics.elidedText(
            path, Qt.TextElideMode.ElideMiddle, _PATH_ELIDE_MAX_CHARS * avg_char_width
        )

    def _show_context_menu(self, position) -> None:
        menu = QMenu(self)
        menu.addAction("Open", lambda: self.open_requested.emit(self._path))
        menu.addAction("Reveal in Folder", lambda: self.reveal_requested.emit(self._path))
        menu.addAction("Copy Path", lambda: self.copy_requested.emit(self._path))
        menu.addAction("Rename...", lambda: self.rename_requested.emit(self._path))
        menu.addAction("Delete", lambda: self.delete_requested.emit(self._path))
        menu.exec(self.mapToGlobal(position))

    def set_theme(self, theme: Theme) -> None:
        for button in (
            self._open_button,
            self._reveal_button,
            self._copy_button,
            self._rename_button,
            self._delete_button,
        ):
            icon_name = button.property("iconName")
            button.setIcon(get_icon(icon_name, theme))
