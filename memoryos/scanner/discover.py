"""Recursive file discovery, filtered to supported extensions.

Deliberately name-agnostic: it does not assume any particular folder layout
(no hardcoded "Pictures"/"PDF"/"PowerPoint" subfolder names). It walks every
root path given to it and classifies each file purely by extension.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from memoryos.utils.extensions import classify, unsupported_reason

# Directories that are part of the tool itself, not user data. Pruned during
# the walk so a venv's bundled sample/test files (site-packages ship plenty
# of stray .docx/.png fixtures) never leak into the index. dist/build/packaging
# (Sprint 6 addition) are PyInstaller's own build output -- tens of thousands
# of DLL/support files that add real scan overhead to the default project-root
# scan otherwise (confirmed: ~19,600 files, enough to make the CLI noticeably
# slower), not a source of indexable content.
DEFAULT_IGNORED_DIRS = {
    ".venv",
    "venv",
    ".git",
    ".index",
    "memoryos",
    "__pycache__",
    "dist",
    "build",
    "packaging",
}


@dataclass
class ScannedFile:
    path: Path
    filename: str
    extension: str
    file_type: str
    mtime: float
    size_bytes: int


@dataclass
class ScanReport:
    files: list[ScannedFile] = field(default_factory=list)
    skipped_unsupported: dict[str, int] = field(default_factory=dict)
    skipped_known_unsupported: dict[str, int] = field(default_factory=dict)


def discover_files(
    roots: list[Path], ignored_dirs: set[str] = DEFAULT_IGNORED_DIRS
) -> ScanReport:
    report = ScanReport()
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in ignored_dirs]
            for name in filenames:
                # Resolved to an absolute canonical path so the same file always
                # produces the same IndexRecord key, regardless of whether the
                # caller passed a relative or absolute root.
                path = (Path(dirpath) / name).resolve()
                _classify_one(path, report)
    return report


def _classify_one(path: Path, report: ScanReport) -> None:
    ext = path.suffix.lower()
    file_type = classify(ext)
    if file_type is not None:
        stat = path.stat()
        report.files.append(
            ScannedFile(
                path=path,
                filename=path.name,
                extension=ext,
                file_type=file_type,
                mtime=stat.st_mtime,
                size_bytes=stat.st_size,
            )
        )
        return

    reason = unsupported_reason(ext)
    if reason is not None:
        report.skipped_known_unsupported[ext] = (
            report.skipped_known_unsupported.get(ext, 0) + 1
        )
    else:
        key = ext or "(no extension)"
        report.skipped_unsupported[key] = report.skipped_unsupported.get(key, 0) + 1
