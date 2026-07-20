"""Sprint 7: curated Fluent UI System Icons (Microsoft, MIT license --
see THIRD_PARTY_LICENSES.md), fetched at build time via
packaging/fetch_icons.sh -- nothing is fetched at runtime. Light/dark
variants are pre-colored SVGs (see that script) so no runtime recoloring
is needed.
"""

from PySide6.QtGui import QIcon

from memoryos.theme import Theme
from memoryos.utils import app_paths


def get_icon(name: str, theme: Theme) -> QIcon:
    """get_resource_dir() is the project root when running from source (so
    this resolves to this same icons/ folder) or the PyInstaller-bundled
    resource dir when frozen -- see packaging/memoryos.spec for the matching
    bundle layout."""
    variant = "dark" if theme == Theme.DARK else "light"
    icon_path = app_paths.get_resource_dir() / "memoryos" / "ui" / "icons" / variant / f"{name}.svg"
    return QIcon(str(icon_path))
