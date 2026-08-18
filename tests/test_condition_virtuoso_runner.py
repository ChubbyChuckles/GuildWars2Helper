from __future__ import annotations

from threading import Event
import unittest
from unittest.mock import patch

from gw2helper.automation import tasks
from gw2helper.services.arcdps_telemetry import CombatTelemetrySnapshot, SkillCooldown


def _ready_rotation_snapshot() -> CombatTelemetrySnapshot:
    return CombatTelemetrySnapshot(
        bridge_status="ArcDPS BHud connected",
        character_loaded=True,
        skills=(SkillCooldown(None, "Weapon_3", "Weapon_3", True, 0.0),),
        buffs=(),
    )


class ConditionVirtuosoRunnerTests(unittest.TestCase):
    def test_sends_adaptive_action_after_foreground_check(self) -> None:
        stop_event = Event()
        sent_keys: list[str] = []
        statuses: list[str] = []

        def send(key: str) -> None:
            sent_keys.append(key)
            stop_event.set()

        with (
            patch.object(tasks, "_activate_gw2_window", return_value=True),
            patch.object(tasks.autoit, "send", side_effect=send),
        ):
            tasks.do_condition_virtuoso_rotation(
                stop_event,
                _ready_rotation_snapshot,
                lambda: False,
                statuses.append,
            )

        self.assertEqual(sent_keys, ["3"])
        self.assertTrue(any("Unstable Bladestorm" in status for status in statuses))

    def test_never_sends_input_when_bridge_is_unavailable(self) -> None:
        stop_event = Event()
        unavailable = CombatTelemetrySnapshot(
            bridge_status="ArcDPS BHud bridge unavailable",
            character_loaded=True,
            skills=(),
            buffs=(),
        )

        def telemetry_supplier() -> CombatTelemetrySnapshot:
            stop_event.set()
            return unavailable

        with patch.object(tasks.autoit, "send") as send:
            tasks.do_condition_virtuoso_rotation(
                stop_event,
                telemetry_supplier,
                lambda: False,
            )

        send.assert_not_called()

    def test_never_sends_input_when_guild_wars_2_cannot_be_foregrounded(self) -> None:
        stop_event = Event()

        def foreground_check() -> bool:
            stop_event.set()
            return False

        with (
            patch.object(tasks, "_activate_gw2_window", side_effect=foreground_check),
            patch.object(tasks.autoit, "send") as send,
        ):
            tasks.do_condition_virtuoso_rotation(
                stop_event,
                _ready_rotation_snapshot,
                lambda: False,
            )

        send.assert_not_called()


if __name__ == "__main__":
    unittest.main()