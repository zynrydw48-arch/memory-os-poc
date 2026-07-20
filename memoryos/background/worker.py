"""Background indexing: runs an indexer's iter_index_files on its own thread,
built via a factory invoked from inside run() (not the constructor) so its
SQLite connection is created on -- and only ever used from -- this thread
(see memoryos/database/db.py's WAL mode note; this is what lets the main
thread keep searching while this thread writes). Reacts to pause/cancel
requests from the main thread; never polls resources itself -- that's
ResourceMonitor's job, driven by a QTimer on the main thread (see
memoryos/ui/main_window.py).
"""

import logging
import threading
import time
from collections.abc import Callable, Iterator
from typing import Protocol

import psutil
from PySide6.QtCore import QThread, Signal

from memoryos.background.resource_monitor import PauseReason
from memoryos.indexing import FileIndexProgress, IndexStats
from memoryos.scanner.discover import ScannedFile
from memoryos.utils.thread_priority import set_current_thread_background_priority

logger = logging.getLogger(__name__)


class IndexerLike(Protocol):
    """The slice of DatabaseIndexer's interface the worker actually needs --
    lets tests substitute a fake, fast indexer with no real ML/database."""

    def prune_missing(self, scanned_files: list[ScannedFile]) -> int: ...
    def iter_index_files(
        self,
        scanned_files: list[ScannedFile],
        resume_event: threading.Event | None = None,
        cancel_event: threading.Event | None = None,
    ) -> Iterator[FileIndexProgress]: ...
    def record_indexing_run(self, **kwargs) -> None: ...
    def close(self) -> None: ...


IndexerFactory = Callable[[], IndexerLike]


class IndexingWorker(QThread):
    # files_done, files_total
    progress = Signal(int, int)
    # PauseReason
    paused = Signal(object)
    resumed = Signal()
    # IndexStats
    finished_indexing = Signal(object)
    # error message
    error = Signal(str)

    def __init__(
        self,
        indexer_factory: IndexerFactory,
        scanned_files: list[ScannedFile],
        parent=None,
    ):
        super().__init__(parent)
        self._indexer_factory = indexer_factory
        self._scanned_files = scanned_files

        self._resume_event = threading.Event()
        self._resume_event.set()  # starts running, not paused
        self._cancel_event = threading.Event()
        self._pause_started_at: float | None = None
        self._paused_seconds_total = 0.0

    def request_pause(self, reason: PauseReason) -> None:
        if self._resume_event.is_set():
            self._resume_event.clear()
            self._pause_started_at = time.time()
            self.paused.emit(reason)

    def request_resume(self) -> None:
        if not self._resume_event.is_set():
            if self._pause_started_at is not None:
                self._paused_seconds_total += time.time() - self._pause_started_at
                self._pause_started_at = None
            self._resume_event.set()
            self.resumed.emit()

    def request_cancel(self) -> None:
        self._cancel_event.set()
        self._resume_event.set()  # wake a paused worker so it can see the cancel

    def run(self) -> None:
        set_current_thread_background_priority()

        indexer: IndexerLike | None = None
        try:
            indexer = self._indexer_factory()

            stats = IndexStats()
            start = time.time()
            stats.pruned = indexer.prune_missing(self._scanned_files)

            total = len(self._scanned_files)
            done = 0
            # Sprint 8.5: the same resume/cancel events drive pause/cancel at
            # two levels now -- the wait()/is_set() below (between yielded
            # items, as before) and, inside iter_index_files itself, whether
            # its internal thread pool starts new work (see
            # memoryos/indexing.py's DatabaseIndexer._process_in_parallel).
            for item in indexer.iter_index_files(
                self._scanned_files,
                resume_event=self._resume_event,
                cancel_event=self._cancel_event,
            ):
                self._accumulate(stats, item)
                done += 1
                self.progress.emit(done, total)

                self._resume_event.wait()  # blocks here while paused, no busy loop
                if self._cancel_event.is_set():
                    break

            stats.elapsed_seconds = time.time() - start

            process = psutil.Process()
            indexer.record_indexing_run(
                duration_seconds=stats.elapsed_seconds,
                files_indexed=stats.indexed,
                cpu_percent=psutil.cpu_percent(interval=None),
                ram_mb=process.memory_info().rss / (1024 * 1024),
                paused_seconds=self._paused_seconds_total,
            )
            self.finished_indexing.emit(stats)
        except Exception as exc:
            logger.exception("indexing worker failed")
            self.error.emit(repr(exc))
        finally:
            if indexer is not None:
                indexer.close()

    @staticmethod
    def _accumulate(stats: IndexStats, item: FileIndexProgress) -> None:
        if item.outcome == "indexed":
            stats.indexed += 1
        elif item.outcome == "unchanged":
            stats.unchanged_skipped += 1
        else:
            stats.errors.append((str(item.scanned_file.path), item.error))
