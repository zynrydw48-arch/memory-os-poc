import sys
import time
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from memoryos.background.resource_monitor import PauseReason
from memoryos.background.worker import IndexingWorker
from memoryos.indexing import FileIndexProgress
from memoryos.scanner.discover import ScannedFile

# QApplication (not QCoreApplication): whichever test module runs first in
# the shared pytest process must create the one real GUI-capable Qt
# application instance, since other modules (e.g. test_main_window.py)
# construct real QWidgets and would otherwise inherit a QCoreApplication that
# can't back them, hanging on construction.
_app = QApplication.instance() or QApplication(sys.argv)

WAIT_TIMEOUT_MS = 5000


def _fake_scanned_files(n: int) -> list[ScannedFile]:
    return [
        ScannedFile(
            path=Path(f"fake_{i}.jpg"),
            filename=f"fake_{i}.jpg",
            extension=".jpg",
            file_type="image",
            mtime=0.0,
            size_bytes=0,
        )
        for i in range(n)
    ]


class FakeIndexer:
    """No real ML/database -- just fast enough to exercise pause/cancel
    timing deterministically, and able to simulate per-file errors."""

    def __init__(self, sleep_seconds: float = 0.03, fail_on: set[str] | None = None):
        self._sleep_seconds = sleep_seconds
        self._fail_on = fail_on or set()
        self.closed = False
        self.recorded_runs: list[dict] = []

    def prune_missing(self, scanned_files: list[ScannedFile]) -> int:
        return 0

    def iter_index_files(
        self,
        scanned_files: list[ScannedFile],
        resume_event=None,
        cancel_event=None,
    ):
        # Sprint 8.5: IndexingWorker.run() now always passes these two
        # kwargs (the real DatabaseIndexer uses them to throttle its
        # internal thread pool's submissions -- see memoryos/indexing.py).
        # This fake stays a simple sequential generator -- it's testing
        # IndexingWorker's own outer wait/cancel loop and signal emission in
        # isolation, not DatabaseIndexer's parallel internals, which have
        # their own dedicated tests in test_database_indexer_parallel.py.
        for f in scanned_files:
            time.sleep(self._sleep_seconds)
            if f.filename in self._fail_on:
                yield FileIndexProgress(scanned_file=f, outcome="error", error="boom")
            else:
                yield FileIndexProgress(scanned_file=f, outcome="indexed")

    def record_indexing_run(self, **kwargs) -> None:
        self.recorded_runs.append(kwargs)

    def close(self) -> None:
        self.closed = True


def _connect_direct(signal, slot):
    signal.connect(slot, Qt.ConnectionType.DirectConnection)


def test_pause_halts_progress_and_resume_continues():
    fake = FakeIndexer(sleep_seconds=0.05)
    files = _fake_scanned_files(10)
    worker = IndexingWorker(lambda: fake, files)

    progress_events = []
    _connect_direct(worker.progress, lambda done, total: progress_events.append(done))

    worker.start()
    time.sleep(0.12)  # let ~2 files process
    worker.request_pause(PauseReason.HIGH_CPU)
    time.sleep(0.1)  # let any file already in flight finish and emit progress
    count_at_pause = len(progress_events)
    time.sleep(0.2)  # would have processed more files if not paused
    assert len(progress_events) == count_at_pause, "progress advanced while paused"

    worker.request_resume()
    finished = worker.wait(WAIT_TIMEOUT_MS)
    assert finished, "worker did not finish after resume"
    assert len(progress_events) == 10


def test_cancel_while_running_stops_early():
    fake = FakeIndexer(sleep_seconds=0.05)
    files = _fake_scanned_files(20)
    worker = IndexingWorker(lambda: fake, files)

    results = []
    _connect_direct(worker.finished_indexing, lambda stats: results.append(stats))

    worker.start()
    time.sleep(0.12)  # let ~2 files process
    worker.request_cancel()
    finished = worker.wait(WAIT_TIMEOUT_MS)

    assert finished
    assert len(results) == 1
    assert results[0].indexed < 20
    assert fake.closed


def test_cancel_while_paused_does_not_deadlock():
    fake = FakeIndexer(sleep_seconds=0.03)
    files = _fake_scanned_files(10)
    worker = IndexingWorker(lambda: fake, files)

    worker.start()
    time.sleep(0.08)
    worker.request_pause(PauseReason.USER_REQUESTED)
    time.sleep(0.05)
    worker.request_cancel()

    finished = worker.wait(WAIT_TIMEOUT_MS)
    assert finished, "worker deadlocked after cancel-while-paused"


def test_per_file_error_does_not_kill_the_run():
    fake = FakeIndexer(sleep_seconds=0.01, fail_on={"fake_2.jpg"})
    files = _fake_scanned_files(5)
    worker = IndexingWorker(lambda: fake, files)

    results = []
    _connect_direct(worker.finished_indexing, lambda stats: results.append(stats))

    worker.start()
    finished = worker.wait(WAIT_TIMEOUT_MS)

    assert finished
    assert len(results) == 1
    stats = results[0]
    assert stats.indexed == 4
    assert len(stats.errors) == 1
    assert stats.errors[0][0] == "fake_2.jpg"


def test_unexpected_setup_failure_emits_error_not_finished():
    def failing_factory():
        raise RuntimeError("setup exploded")

    files = _fake_scanned_files(3)
    worker = IndexingWorker(failing_factory, files)

    errors = []
    finished_signals = []
    _connect_direct(worker.error, lambda msg: errors.append(msg))
    _connect_direct(worker.finished_indexing, lambda stats: finished_signals.append(stats))

    worker.start()
    finished = worker.wait(WAIT_TIMEOUT_MS)

    assert finished
    assert len(errors) == 1
    assert "setup exploded" in errors[0]
    assert finished_signals == []


def test_paused_seconds_recorded_on_finish():
    fake = FakeIndexer(sleep_seconds=0.02)
    files = _fake_scanned_files(5)
    worker = IndexingWorker(lambda: fake, files)

    worker.start()
    time.sleep(0.03)
    worker.request_pause(PauseReason.USER_REQUESTED)
    time.sleep(0.15)
    worker.request_resume()
    finished = worker.wait(WAIT_TIMEOUT_MS)

    assert finished
    assert len(fake.recorded_runs) == 1
    assert fake.recorded_runs[0]["paused_seconds"] == pytest.approx(0.15, abs=0.1)
