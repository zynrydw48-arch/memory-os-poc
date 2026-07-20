"""Frozen-aware path resolution (Sprint 6). Running from source, resources
live alongside the project as they always have; when frozen by PyInstaller,
bundled resources are extracted to sys._MEIPASS and user data must go to a
writable per-user directory instead of the (possibly read-only) install dir.
"""

import os
import sys
from pathlib import Path

APP_NAME = "MemoryOS"

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def get_resource_dir() -> Path:
    """Base directory for bundled, read-only resources (tessdata, the
    Tesseract binary, the offline model cache)."""
    if is_frozen():
        return Path(sys._MEIPASS)
    return _PROJECT_ROOT


def get_user_data_dir() -> Path:
    """Writable, per-user directory for the database and other runtime state.
    %APPDATA%\\MemoryOS when frozen; the project's own .memoryos/ directory
    when running from source, matching existing dev behavior exactly."""
    if is_frozen():
        base = Path(os.environ.get("APPDATA", str(Path.home())))
        data_dir = base / APP_NAME
    else:
        data_dir = _PROJECT_ROOT / ".memoryos"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir
