from __future__ import annotations

from threading import Event
import time
import unittest
from unittest.mock import patch

from gw2helper.automation import tasks
from gw2helper.automation.condition_virtuoso import ConditionVirtuosoPlanner
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
                planner=ConditionVirtuosoPlanner(use_opener=False),
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
                planner=ConditionVirtuosoPlanner(use_opener=False),
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
                planner=ConditionVirtuosoPlanner(use_opener=False),
            )

        send.assert_not_called()

    def test_stops_when_native_activation_is_a_wrong_offhand_skill(self) -> None:
        stop_event = Event()
        statuses: list[str] = []
        snapshots = iter((_ready_rotation_snapshot(),))

        def telemetry_supplier() -> CombatTelemetrySnapshot:
            try:
                return next(snapshots)
            except StopIteration:
                return CombatTelemetrySnapshot(
                    bridge_status="ArcDPS BHud connected",
                    character_loaded=True,
                    skills=(),
                    buffs=(),
                    last_skill_id=10280,
                    skill_activation_sequence=1,
                    last_skill_activated_at=time.monotonic(),
                )

        with (
            patch.object(tasks, "_activate_gw2_window", return_value=True),
            patch.object(tasks.autoit, "send"),
        ):
            tasks.do_condition_virtuoso_rotation(
                stop_event,
                telemetry_supplier,
                lambda: False,
                statuses.append,
                planner=ConditionVirtuosoPlanner(use_opener=False),
            )

        self.assertTrue(stop_event.is_set())
        self.assertTrue(any("expected skill" in status for status in statuses))

    def test_ignores_unrelated_native_activations_while_cast_is_pending(self) -> None:
        stop_event = Event()
        statuses: list[str] = []
        snapshots = iter(
            (
                _ready_rotation_snapshot(),
                CombatTelemetrySnapshot(
                    bridge_status="ArcDPS BHud connected",
                    character_loaded=True,
                    skills=(),
                    buffs=(),
                    last_skill_id=62510,
                    skill_activation_sequence=1,
                    last_skill_activated_at=time.monotonic(),
                ),
                CombatTelemetrySnapshot(
                    bridge_status="ArcDPS BHud connected",
                    character_loaded=True,
                    skills=(),
                    buffs=(),
                    last_skill_id=62607,
                    skill_activation_sequence=2,
                    last_skill_activated_at=time.monotonic(),
                ),
            )
        )

        def telemetry_supplier() -> CombatTelemetrySnapshot:
            try:
                return next(snapshots)
            except StopIteration:
                stop_event.set()
                return CombatTelemetrySnapshot(
                    bridge_status="ArcDPS BHud connected",
                    character_loaded=True,
                    skills=(),
                    buffs=(),
                )

        with (
            patch.object(tasks, "_activate_gw2_window", return_value=True),
            patch.object(tasks.autoit, "send"),
        ):
            tasks.do_condition_virtuoso_rotation(
                stop_event,
                telemetry_supplier,
                lambda: False,
                statuses.append,
                planner=ConditionVirtuosoPlanner(use_opener=False),
            )

        self.assertFalse(any("stopped: expected skill" in status for status in statuses))


if __name__ == "__main__":
    unittest.main()