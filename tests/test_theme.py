import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from memoryos.theme import Theme, apply_theme, resolve_effective_theme

_app = QApplication.instance() or QApplication(sys.argv)


def _provider(scheme: Qt.ColorScheme):
    return lambda: scheme


def test_light_and_dark_pass_through_regardless_of_system_scheme():
    assert resolve_effective_theme(Theme.LIGHT, _provider(Qt.ColorScheme.Dark)) == Theme.LIGHT
    assert resolve_effective_theme(Theme.DARK, _provider(Qt.ColorScheme.Light)) == Theme.DARK


def test_system_resolves_to_dark_when_os_is_dark():
    assert resolve_effective_theme(Theme.SYSTEM, _provider(Qt.ColorScheme.Dark)) == Theme.DARK


def test_system_resolves_to_light_when_os_is_light():
    assert resolve_effective_theme(Theme.SYSTEM, _provider(Qt.ColorScheme.Light)) == Theme.LIGHT


def test_system_falls_back_to_light_when_os_scheme_unknown():
    assert resolve_effective_theme(Theme.SYSTEM, _provider(Qt.ColorScheme.Unknown)) == Theme.LIGHT


def test_apply_dark_theme_changes_palette_and_light_restores_it():
    original_palette = _app.palette()
    original_style_name = _app.style().objectName()

    apply_theme(_app, Theme.DARK, original_palette, original_style_name)
    assert _app.palette() != original_palette

    apply_theme(_app, Theme.LIGHT, original_palette, original_style_name)
    assert _app.palette() == original_palette
