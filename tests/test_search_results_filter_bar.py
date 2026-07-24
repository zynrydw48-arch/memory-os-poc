import sys

from PySide6.QtWidgets import QApplication

from memoryos.ui.search_results_filter_bar import SearchResultsFilterBar

_app = QApplication.instance() or QApplication(sys.argv)


def test_all_tab_checked_by_default():
    bar = SearchResultsFilterBar()
    assert bar._buttons["All"].isChecked()
    for label, button in bar._buttons.items():
        if label != "All":
            assert not button.isChecked()


def test_clicking_a_tab_makes_it_exclusively_checked():
    bar = SearchResultsFilterBar()
    bar._buttons["Images"].click()

    assert bar._buttons["Images"].isChecked()
    assert not bar._buttons["All"].isChecked()


def test_clicking_a_tab_emits_filter_selected():
    bar = SearchResultsFilterBar()
    received = []
    bar.filter_selected.connect(received.append)

    bar._buttons["Web"].click()

    assert received == ["Web"]


def test_reset_restores_all_tab():
    bar = SearchResultsFilterBar()
    bar._buttons["Notes"].click()
    assert bar._buttons["Notes"].isChecked()

    bar.reset()

    assert bar._buttons["All"].isChecked()
    assert not bar._buttons["Notes"].isChecked()
