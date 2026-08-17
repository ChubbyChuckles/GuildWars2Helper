from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from gw2helper.services import arc_client


class _FakeMumbleLink:
    def __init__(self, ticks: list[int], process_id: int = 1234) -> None:
        self._ticks = iter(ticks)
        self._process_id = process_id
        self.closed = False

    def read(self):
        return (
            SimpleNamespace(uiTick=next(self._ticks)),
            SimpleNamespace(processId=self._process_id),
        )

    def close(self) -> None:
        self.closed = True


class CharacterSelectDetectionTests(unittest.TestCase):
    def test_static_ui_tick_means_character_select(self) -> None:
        mumble_link = _FakeMumbleLink([1450, 1450])

        with (
            patch.object(arc_client, "MumbleLink", return_value=mumble_link),
            patch.object(arc_client, "_is_gw2_process", return_value=True),
            patch.object(arc_client.time, "monotonic", side_effect=[0.0, 0.0, 0.5]),
            patch.object(arc_client.time, "sleep"),
        ):
            is_at_character_select = arc_client.is_in_char_select_screen(
                timeout=0.5
            )

        self.assertTrue(is_at_character_select)
        self.assertTrue(mumble_link.closed)

    def test_advancing_ui_tick_means_character_is_loaded(self) -> None:
        mumble_link = _FakeMumbleLink([1450, 1451])

        with (
            patch.object(arc_client, "MumbleLink", return_value=mumble_link),
            patch.object(arc_client, "_is_gw2_process", return_value=True),
            patch.object(arc_client.time, "monotonic", side_effect=[0.0, 0.0]),
            patch.object(arc_client.time, "sleep"),
        ):
            is_at_character_select = arc_client.is_in_char_select_screen(
                timeout=0.5
            )

        self.assertFalse(is_at_character_select)
        self.assertTrue(mumble_link.closed)

    def test_unknown_process_returns_no_state(self) -> None:
        mumble_link = _FakeMumbleLink([1450])

        with (
            patch.object(arc_client, "MumbleLink", return_value=mumble_link),
            patch.object(arc_client, "_is_gw2_process", return_value=False),
        ):
            is_at_character_select = arc_client.is_in_char_select_screen()

        self.assertIsNone(is_at_character_select)
        self.assertTrue(mumble_link.closed)


if __name__ == "__main__":
    unittest.main()