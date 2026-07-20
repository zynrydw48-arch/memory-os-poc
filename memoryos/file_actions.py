"""Sprint 4: pure, Qt-free filesystem operations for search-result actions
(Open, Reveal in Folder, Rename, Delete). No Database/UI dependency here --
easy to unit test without a running app; memoryos/ui/main_window.py wires
these into the results table's context menu and keeps the index in sync via
Database.update_file_path/delete_file_by_path.
"""

import os
import subprocess
from pathlib import Path

import send2trash

_INVALID_FILENAME_CHARS = set('<>:"/\\|?*')


def is_valid_filename(name: str) -> bool:
    if not name or not name.strip():
        return False
    return not any(char in _INVALID_FILENAME_CHARS for char in name)


def open_file(path: Path) -> None:
    os.startfile(path)  # noqa: S606 -- Windows-only by design, see README prerequisites


def reveal_in_folder(path: Path) -> None:
    subprocess.run(["explorer", "/select,", str(path)])


def rename_file(path: Path, new_filename: str) -> Path:
    if not is_valid_filename(new_filename):
        raise ValueError(f"Invalid filename: {new_filename!r}")
    new_path = path.with_name(new_filename)
    path.rename(new_path)  # raises FileExistsError if new_path already exists
    return new_path


def delete_file(path: Path) -> None:
    send2trash.send2trash(path)  # moves to the Recycle Bin, never a permanent delete
