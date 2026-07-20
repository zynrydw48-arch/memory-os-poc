"""Sprint 9: a windowed (console=False) frozen build has no console at all --
Windows leaves sys.stdout/sys.stderr as None in that case, so any leftover
print() call anywhere (including inside a dependency) would itself crash the
app with an AttributeError. This guards against that and gives uncaught
exceptions a place to land instead of vanishing silently, since there's no
console left to print a traceback to.
"""

import sys
import traceback
from datetime import datetime
from pathlib import Path

from memoryos.utils import app_paths

CRASH_LOG_FILENAME = "crash.log"


def install_crash_logging(is_frozen: bool | None = None) -> None:
    """Call once, early in the frozen entrypoint (memoryos/app_main.py),
    before anything else runs -- so it also catches exceptions during model
    loading, not just once the UI is up. No-op when running from source,
    where a real console is always attached. is_frozen defaults to
    app_paths.is_frozen(); overridable for testing."""
    if is_frozen is None:
        is_frozen = app_paths.is_frozen()
    if not is_frozen:
        return

    log_path = app_paths.get_user_data_dir() / CRASH_LOG_FILENAME

    if sys.stdout is None or sys.stderr is None:
        log_stream = open(log_path, "a", encoding="utf-8")
        if sys.stdout is None:
            sys.stdout = log_stream
        if sys.stderr is None:
            sys.stderr = log_stream

    sys.excepthook = _build_excepthook(log_path)


def _build_excepthook(log_path: Path):
    def _log_uncaught_exception(exc_type, exc_value, exc_tb) -> None:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- {datetime.now().isoformat()} ---\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)

    return _log_uncaught_exception
