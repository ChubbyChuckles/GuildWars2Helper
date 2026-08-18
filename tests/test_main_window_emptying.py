from __future__ import annotations

import unittest
from unittest.mock import patch

from PyQt6 import QtWidgets

from gw2helper import constants, persistence
from gw2helper.services.gw2_api import BankSummary
from gw2helper.ui.main_window import MainWindow


class MainWindowEmptyingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self) -> None:
        constants.set_empty_chars_enabled(False)
        self.state = persistence.AppState(
            farming_days_since_empty=[f"2026-08-{day:02}" for day in range(1, 8)]
        )
        self._load_state = patch(
            "gw2helper.ui.main_window.persistence.load_app_state",
            return_value=self.state,
        )
        self._load_characters = patch(
            "gw2helper.ui.main_window.tasks.get_character_list",
            return_value=[],
        )
        self._load_bank = patch(
            "gw2helper.ui.main_window.TaskController.load_bank_summary",
            return_value=False,
        )
        self._load_state.start()
        self._load_characters.start()
        self._load_bank.start()
        self.window = MainWindow()

    def tearDown(self) -> None:
        self.window.close()
        self._load_bank.stop()
        self._load_characters.stop()
        self._load_state.stop()
        constants.set_empty_chars_enabled(False)

    def test_due_schedule_checks_empty_character_on_startup(self) -> None:
        self.assertTrue(self.window.empty_checkbox.isChecked())
        self.assertEqual(self.window.farm_count_pill.text(), "Emptying: Due")

    def test_successful_emptying_resets_cycle_and_unchecks_checkbox(self) -> None:
        self.window._on_farming_completed(
            {"characters_farmed": 1, "emptied": True}
        )

        self.assertFalse(self.window.empty_checkbox.isChecked())
        self.assertEqual(self.state.farming_days_since_empty, [])
        self.assertEqual(self.state.character_farm_counts_since_empty, {})
        self.assertEqual(self.state.farm_count_since_empty, 0)

    def test_bank_summary_is_displayed(self) -> None:
        self.window._on_bank_summary_loaded(BankSummary(570, 40, 3, 2))

        self.assertEqual(self.window.bank_slots_pill.text(), "Bank 40/570")
        self.assertEqual(self.window.bank_rare_pill.text(), "Rare 3")
        self.assertEqual(self.window.bank_exotic_pill.text(), "Exotic 2")


if __name__ == "__main__":
    unittest.main()