"""Bug-fix regression tests: Rename/Delete refreshing results must NOT record
a new Search History entry, while a normal user-initiated search (including
re-running one from the history panel) still must.

Uses a fake, instant EmbeddingProvider so these tests don't need to load the
real ML models -- MainWindow never calls anything on ocr_engine/vision_pipeline
until indexing starts, which these tests never trigger, so those are passed
as None.
"""

import sys

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox

from memoryos import file_actions
from memoryos.database.db import Database, FileRecord
from memoryos.theme import Theme
from memoryos.ui.main_window import MainWindow

_app = QApplication.instance() or QApplication(sys.argv)

EMBED_DIM = 8


class FakeEmbeddingProvider:
    @property
    def dimension(self) -> int:
        return EMBED_DIM

    @property
    def model_name(self) -> str:
        return "fake"

    def encode(self, texts):
        vectors = np.ones((len(texts), EMBED_DIM), dtype=np.float32)
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors


@pytest.fixture
def window(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    database = Database(db_path)

    file_path = tmp_path / "note.txt"
    file_path.write_text("hello", encoding="utf-8")

    embedding = np.ones(EMBED_DIM, dtype=np.float32)
    embedding /= np.linalg.norm(embedding)
    database.upsert_file(
        FileRecord(
            id="id-1",
            path=str(file_path),
            filename="note.txt",
            extension=".txt",
            file_type="text",
            semantic_text="a note",
            metadata={},
            mtime=1.0,
            indexed_at=1.0,
        ),
        embedding,
    )

    win = MainWindow(FakeEmbeddingProvider(), None, None, database, db_path)
    yield win
    database.close()


@pytest.fixture
def empty_window(tmp_path):
    db_path = tmp_path / "empty.sqlite3"
    database = Database(db_path)
    win = MainWindow(FakeEmbeddingProvider(), None, None, database, db_path)
    yield win
    database.close()


def test_normal_search_records_history(window):
    window._search_line_edit.setText("a note")
    window._on_search()

    assert len(window._database.get_recent_searches()) == 1
    assert len(window._results_view._cards) == 1
    assert window._results_stack.currentWidget() is window._results_view


def test_history_entry_click_still_records_a_new_entry(window):
    window._search_line_edit.setText("a note")
    window._on_search()
    assert len(window._database.get_recent_searches()) == 1

    window._on_history_entry_selected("a note")
    assert len(window._database.get_recent_searches()) == 2


def test_rename_refresh_does_not_record_history(window, monkeypatch):
    window._search_line_edit.setText("a note")
    window._on_search()
    assert len(window._database.get_recent_searches()) == 1

    hit_path = window._last_hits[0].path
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("renamed.txt", True))

    window._on_rename_file(hit_path)

    assert len(window._database.get_recent_searches()) == 1  # unchanged
    assert len(window._results_view._cards) == 1
    assert window._results_view._cards[0].filename_label.text() == "renamed.txt"


def test_delete_refresh_does_not_record_history(window, monkeypatch):
    window._search_line_edit.setText("a note")
    window._on_search()
    assert len(window._database.get_recent_searches()) == 1

    hit_path = window._last_hits[0].path
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes
    )
    monkeypatch.setattr(file_actions.send2trash, "send2trash", lambda p: None)

    window._on_delete_file(hit_path)

    assert len(window._database.get_recent_searches()) == 1  # unchanged
    assert len(window._results_view._cards) == 0
    # The deleted file was the only indexed file -- results area should have
    # flipped back to the empty state, not be left showing a blank ResultsView.
    assert window._results_stack.currentWidget() is window._empty_state


def test_selecting_theme_persists_setting_without_affecting_search(window):
    try:
        window._on_theme_selected(Theme.DARK)
        assert window._database.get_setting("theme") == "dark"

        window._search_line_edit.setText("a note")
        window._on_search()
        assert len(window._database.get_recent_searches()) == 1
        assert len(window._results_view._cards) == 1
    finally:
        # Reset the shared QApplication's palette so this doesn't leak a dark
        # theme into other tests -- QApplication is a per-process singleton.
        window._on_theme_selected(Theme.LIGHT)


def test_empty_state_shown_when_nothing_indexed(empty_window):
    assert empty_window._results_stack.currentWidget() is empty_window._empty_state


def test_results_view_shown_once_a_file_is_indexed(empty_window, tmp_path):
    file_path = tmp_path / "later.txt"
    file_path.write_text("hello", encoding="utf-8")
    embedding = np.ones(EMBED_DIM, dtype=np.float32)
    embedding /= np.linalg.norm(embedding)
    empty_window._database.upsert_file(
        FileRecord(
            id="id-2",
            path=str(file_path),
            filename="later.txt",
            extension=".txt",
            file_type="text",
            semantic_text="a note",
            metadata={},
            mtime=1.0,
            indexed_at=1.0,
        ),
        embedding,
    )

    # Mirrors what _on_worker_finished does after a real indexing run.
    empty_window._refresh_results_visibility()

    assert empty_window._results_stack.currentWidget() is empty_window._results_view


def test_empty_state_browse_button_wired_to_on_browse(empty_window, monkeypatch, tmp_path):
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **k: str(tmp_path))

    empty_window._empty_state._browse_button.click()

    assert empty_window._folder_line_edit.text() == str(tmp_path)


def test_populated_window_shows_results_view_not_empty_state(window):
    assert window._results_stack.currentWidget() is window._results_view


def test_about_action_shows_version_and_attribution(window, monkeypatch):
    from memoryos.__version__ import __version__

    calls = []
    monkeypatch.setattr(
        QMessageBox, "about", lambda parent, title, text: calls.append((title, text))
    )

    window._on_about()

    assert len(calls) == 1
    title, text = calls[0]
    assert title == "About MemoryOS"
    assert __version__ in text
    assert "Fluent UI System Icons" in text
