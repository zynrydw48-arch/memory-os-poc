import sys

from PySide6.QtWidgets import QApplication

from memoryos.ui.filter_empty_state import FilterEmptyState

_app = QApplication.instance() or QApplication(sys.argv)


def test_set_message_uses_literal_lowercased_category():
    widget = FilterEmptyState()
    widget.set_message("Notes", "white dog")

    assert widget._message_label.text() == "We couldn't find any notes matching 'white dog'"


def test_set_message_maps_more_to_other_files():
    widget = FilterEmptyState()
    widget.set_message("More...", "quarterly report")

    assert (
        widget._message_label.text()
        == "We couldn't find any other files matching 'quarterly report'"
    )


def test_set_message_for_each_normal_category():
    widget = FilterEmptyState()
    for category, expected_word in [("Images", "images"), ("Web", "web"), ("Files", "files")]:
        widget.set_message(category, "cats")
        assert widget._message_label.text() == f"We couldn't find any {expected_word} matching 'cats'"
