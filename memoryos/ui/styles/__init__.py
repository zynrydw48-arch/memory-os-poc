"""Sprint 7: QSS loader. Frozen-aware the same way memoryos/ui/icons.py is."""

from memoryos.theme import Theme
from memoryos.utils import app_paths


def load_stylesheet(theme: Theme) -> str:
    filename = "dark.qss" if theme == Theme.DARK else "light.qss"
    path = app_paths.get_resource_dir() / "memoryos" / "ui" / "styles" / filename
    return path.read_text(encoding="utf-8")
