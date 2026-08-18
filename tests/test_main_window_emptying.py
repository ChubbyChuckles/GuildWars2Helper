from __future__ import annotations

import unittest
from unittest.mock import patch

from PyQt6 import QtCore, QtGui, QtWidgets

from gw2helper import constants, persistence
from gw2helper.services.arcdps_telemetry import (
    ActiveBuff,
    CombatTelemetrySnapshot,
    SkillCooldown,
)
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

    def test_api_errors_are_shown_in_the_interface(self) -> None:
        self.window._on_characters_load_failed("GW2_API_KEY is missing characters scope.")
        self.window._on_bank_summary_failed("GW2_API_KEY is missing account scope.")

        self.assertEqual(self.window.character_combo.currentText(), "Characters unavailable")
        self.assertFalse(self.window.character_combo.isEnabled())
        self.assertEqual(self.window.bank_slots_pill.text(), "Bank Unavailable")
        self.assertIn("account scope", self.window.status_label.text())

    def test_idle_combat_control_starts_rotation(self) -> None:
        with patch.object(self.window.controller, "toggle_rotation", return_value=True) as toggle:
            self.window._toggle_pause()

        self.assertEqual(self.window.pause_button.text(), "Start Rotation")
        self.assertTrue(self.window.pause_button.isEnabled())
        toggle.assert_called_once_with()

    def test_pause_key_toggles_rotation_when_farming_is_idle(self) -> None:
        event = QtGui.QKeyEvent(
            QtCore.QEvent.Type.KeyPress,
            QtCore.Qt.Key.Key_Pause,
            QtCore.Qt.KeyboardModifier.NoModifier,
        )
        with patch.object(self.window, "_toggle_pause") as toggle:
            self.window.keyPressEvent(event)

        self.assertTrue(event.isAccepted())
        toggle.assert_called_once_with()

    def test_combat_telemetry_panel_renders_skill_and_buff_data(self) -> None:
        snapshot = CombatTelemetrySnapshot(
            bridge_status="ArcDPS BHud connected",
            character_loaded=True,
            skills=(SkillCooldown(14375, "Arcing Slice", "Profession_1", False, 4.2),),
            buffs=(ActiveBuff(1187, "Quickness", 1, 2.5),),
        )
        with patch.object(
            self.window.controller,
            "combat_telemetry_snapshot",
            return_value=snapshot,
        ):
            self.window._refresh_combat_telemetry()

        self.assertEqual(self.window.combat_bridge_label.text(), "ArcDPS BHud connected")
        self.assertEqual(self.window.combat_skills_table.item(0, 0).text(), "Arcing Slice")
        self.assertEqual(self.window.combat_skills_table.item(0, 2).text(), "4.2s")
        self.assertEqual(self.window.combat_buffs_table.item(0, 0).text(), "Quickness")


if __name__ == "__main__":
    unittest.main()