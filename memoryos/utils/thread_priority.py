"""Windows thread-priority helper, shared by every indexing-related thread
(the IndexingWorker QThread itself, and, as of Sprint 8.5, each parallel
extraction/vision worker thread spawned by DatabaseIndexer's thread pool --
see memoryos/indexing.py). Lives here rather than in
memoryos/background/worker.py so memoryos/indexing.py can use it too without
a circular import (worker.py already imports from indexing.py)."""

import ctypes
import logging

logger = logging.getLogger(__name__)

# WinBase.h: SetThreadPriority special value. Tells Windows to deprioritize
# both CPU scheduling and disk I/O for this thread, continuously, with no
# polling required -- the "always be polite" baseline layer of throttling.
_THREAD_MODE_BACKGROUND_BEGIN = 0x00010000


def set_current_thread_background_priority() -> None:
    """Best-effort: a failure here should never prevent indexing from
    running, just make it slightly less polite about CPU/disk scheduling."""
    try:
        handle = ctypes.windll.kernel32.GetCurrentThread()
        ctypes.windll.kernel32.SetThreadPriority(handle, _THREAD_MODE_BACKGROUND_BEGIN)
    except Exception:
        logger.exception("failed to set background thread priority")
