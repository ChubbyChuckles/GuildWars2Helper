from __future__ import annotations

import unittest

from gw2helper import constants
from gw2helper.automation import tasks


class EmptyCharacterModeTests(unittest.TestCase):
    def tearDown(self) -> None:
        constants.set_empty_chars_enabled(False)

    def test_normal_farming_skips_a_character_already_farmed_today(self) -> None:
        self.assertTrue(tasks._should_skip_character(lambda _name: True, "Caithe"))

    def test_empty_character_mode_farms_previously_farmed_characters(self) -> None:
        constants.set_empty_chars_enabled(True)

        self.assertFalse(tasks._should_skip_character(lambda _name: True, "Caithe"))


if __name__ == "__main__":
    unittest.main()