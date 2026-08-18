from __future__ import annotations

import unittest
from unittest.mock import patch

from gw2helper.automation import tasks


class CharacterSelectionClickTests(unittest.TestCase):
    def test_does_not_click_when_guild_wars_2_is_not_foreground(self) -> None:
        with (
            patch.object(tasks.autoit, "win_active", side_effect=[0, 0]),
            patch.object(tasks.autoit, "win_activate") as win_activate,
            patch.object(tasks.autoit, "mouse_click") as mouse_click,
            patch.object(tasks.time, "sleep"),
        ):
            clicked = tasks._click_character_selection_slot(3610, 2062)

        self.assertFalse(clicked)
        win_activate.assert_called_once_with("Guild Wars 2")
        mouse_click.assert_not_called()

    def test_clicks_character_slot_when_guild_wars_2_is_foreground(self) -> None:
        with (
            patch.object(tasks.autoit, "win_active", return_value=1),
            patch.object(tasks.autoit, "mouse_click") as mouse_click,
        ):
            clicked = tasks._click_character_selection_slot(3610, 2062)

        self.assertTrue(clicked)
        mouse_click.assert_called_once_with("left", 3610, 2062, 2, 0)

    def test_clicks_after_guild_wars_2_is_activated(self) -> None:
        with (
            patch.object(tasks.autoit, "win_active", side_effect=[0, 1]),
            patch.object(tasks.autoit, "win_activate") as win_activate,
            patch.object(tasks.autoit, "mouse_click") as mouse_click,
            patch.object(tasks.time, "sleep"),
        ):
            clicked = tasks._click_character_selection_slot(3610, 2062)

        self.assertTrue(clicked)
        win_activate.assert_called_once_with("Guild Wars 2")
        mouse_click.assert_called_once_with("left", 3610, 2062, 2, 0)


if __name__ == "__main__":
    unittest.main()