import sys

from memoryos.utils import crash_logging


def test_noop_when_not_frozen(monkeypatch, tmp_path):
    original_excepthook = sys.excepthook
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    crash_logging.install_crash_logging(is_frozen=False)

    assert sys.stdout is None  # untouched
    assert sys.stderr is None  # untouched
    assert sys.excepthook is original_excepthook  # untouched


def test_redirects_none_stdout_and_stderr_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "memoryos.utils.app_paths.get_user_data_dir", lambda: tmp_path
    )
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    crash_logging.install_crash_logging(is_frozen=True)

    assert sys.stdout is not None
    assert sys.stderr is not None
    assert sys.stdout is sys.stderr  # both share the same log stream

    sys.stdout.write("hello from a windowed build\n")
    sys.stdout.flush()
    log_path = tmp_path / crash_logging.CRASH_LOG_FILENAME
    assert "hello from a windowed build" in log_path.read_text(encoding="utf-8")


def test_leaves_a_real_console_alone_when_frozen(monkeypatch, tmp_path):
    # A frozen console=True build (or any case where stdout/stderr are real
    # streams, not None) shouldn't have them swapped out.
    monkeypatch.setattr(
        "memoryos.utils.app_paths.get_user_data_dir", lambda: tmp_path
    )
    real_stdout = sys.stdout
    real_stderr = sys.stderr

    crash_logging.install_crash_logging(is_frozen=True)

    assert sys.stdout is real_stdout
    assert sys.stderr is real_stderr


def test_excepthook_logs_uncaught_exception_traceback(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "memoryos.utils.app_paths.get_user_data_dir", lambda: tmp_path
    )
    original_excepthook = sys.excepthook

    crash_logging.install_crash_logging(is_frozen=True)
    try:
        assert sys.excepthook is not original_excepthook

        try:
            raise ValueError("boom from a test exception")
        except ValueError:
            sys.excepthook(*sys.exc_info())

        log_path = tmp_path / crash_logging.CRASH_LOG_FILENAME
        content = log_path.read_text(encoding="utf-8")
        assert "ValueError" in content
        assert "boom from a test exception" in content
    finally:
        sys.excepthook = original_excepthook
