from __future__ import annotations

from threading import Event
import time
import unittest
from unittest.mock import patch

from gw2helper.automation import tasks
from gw2helper.automation.condition_virtuoso import (
    ConditionVirtuosoPlanner,
    RotationDecision,
)
from gw2helper.services.arcdps_telemetry import (
    CombatTelemetrySnapshot,
    SkillActivation,
    SkillCooldown,
)


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

    def test_commits_action_without_waiting_for_native_audit(self) -> None:
        stop_event = Event()
        planner = ConditionVirtuosoPlanner(use_opener=False)
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
                    last_skill_id=62607,
                    skill_activation_sequence=1,
                    last_skill_activated_at=time.monotonic(),
                    skill_activations=(
                        SkillActivation(62607, time.monotonic(), 1),
                    ),
                )

        original_record_action = planner.record_action

        def record_action(decision, now: float) -> None:
            original_record_action(decision, now)
            stop_event.set()

        with (
            patch.object(tasks, "_activate_gw2_window", return_value=True),
            patch.object(tasks.autoit, "send"),
            patch.object(planner, "record_action", side_effect=record_action) as record,
        ):
            tasks.do_condition_virtuoso_rotation(
                stop_event,
                telemetry_supplier,
                lambda: False,
                planner=planner,
            )

        record.assert_called_once()

    def test_confirms_a_post_send_activation_with_a_delayed_event_timestamp(self) -> None:
        decision = RotationDecision(
            key="5",
            label="Phantasmal Swordsman",
            slot="Weapon_5",
            delay_seconds=0.82,
            reason="test",
            expected_skill_ids=(10174,),
        )
        pending = tasks._PendingRotationAction(
            decision=decision,
            baseline_sequence=4,
            sent_at=100.0,
            deadline=101.2,
        )
        snapshot = CombatTelemetrySnapshot(
            bridge_status="ArcDPS BHud connected",
            character_loaded=True,
            skills=(),
            buffs=(),
            skill_activation_sequence=5,
            skill_activations=(SkillActivation(10174, 99.6, 5),),
        )

        confirmed, observed = tasks._pending_action_result(pending, snapshot, 100.2)

        self.assertEqual(confirmed, SkillActivation(10174, 99.6, 5))
        self.assertIsNone(observed)

    def test_does_not_block_later_actions_while_native_audit_is_pending(self) -> None:
        stop_event = Event()
        sent_keys: list[str] = []

        class SequentialPlanner:
            def __init__(self) -> None:
                self._decisions = [
                    RotationDecision(
                        key="3",
                        label="Unstable Bladestorm",
                        slot="Weapon_3",
                        delay_seconds=0.0,
                        reason="test",
                        expected_skill_ids=(62607,),
                    ),
                    RotationDecision(
                        key="2",
                        label="Bladecall",
                        slot="Weapon_2",
                        delay_seconds=0.0,
                        reason="test",
                        expected_skill_ids=(62560,),
                    ),
                ]
                self.recorded: list[RotationDecision] = []

            def choose(self, *_args, **_kwargs):
                return self._decisions.pop(0) if self._decisions else None

            def record_action(self, decision, _now: float) -> None:
                self.recorded.append(decision)

            def recover_from_interruption(self, *_args, **_kwargs) -> None:
                pass

            def disable_binding(self, *_args, **_kwargs) -> None:
                pass

        planner = SequentialPlanner()
        scans = 0

        def telemetry_supplier() -> CombatTelemetrySnapshot:
            nonlocal scans
            scans += 1
            if scans >= 3:
                stop_event.set()
            return _ready_rotation_snapshot()

        def send(key: str) -> None:
            sent_keys.append(key)
            if len(sent_keys) == 2:
                stop_event.set()

        with (
            patch.object(tasks, "_activate_gw2_window", return_value=True),
            patch.object(tasks.autoit, "send", side_effect=send),
        ):
            tasks.do_condition_virtuoso_rotation(
                stop_event,
                telemetry_supplier,
                lambda: False,
                planner=planner,
            )

        self.assertEqual(sent_keys, ["3", "2"])
        self.assertEqual([decision.key for decision in planner.recorded], ["3", "2"])

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

    def test_reports_known_mismatched_native_activation(self) -> None:
        decision = RotationDecision(
            key="q",
            label="Signet of Illusions",
            slot="Utility_Illusions",
            delay_seconds=0.12,
            reason="test",
            expected_skill_ids=(10247,),
        )
        pending = tasks._PendingRotationAction(
            decision=decision,
            baseline_sequence=0,
            sent_at=100.0,
            deadline=101.2,
        )
        snapshot = CombatTelemetrySnapshot(
            bridge_status="ArcDPS BHud connected",
            character_loaded=True,
            skills=(),
            buffs=(),
            skill_activation_sequence=1,
            skill_activations=(SkillActivation(10234, 100.1, 1),),
        )

        confirmed, observed = tasks._pending_action_result(pending, snapshot, 101.3)

        self.assertIsNone(confirmed)
        self.assertEqual(observed, SkillActivation(10234, 100.1, 1))

    def test_ignores_unrelated_native_activation_when_audit_expires(self) -> None:
        decision = RotationDecision(
            key="2",
            label="Bladecall",
            slot="Weapon_2",
            delay_seconds=0.42,
            reason="test",
            expected_skill_ids=(62560,),
        )
        pending = tasks._PendingRotationAction(
            decision=decision,
            baseline_sequence=0,
            sent_at=100.0,
            deadline=102.5,
        )
        snapshot = CombatTelemetrySnapshot(
            bridge_status="ArcDPS BHud connected",
            character_loaded=True,
            skills=(),
            buffs=(),
            skill_activation_sequence=1,
            skill_activations=(SkillActivation(62586, 100.1, 1),),
        )

        confirmed, observed = tasks._pending_action_result(pending, snapshot, 103.0)

        self.assertIsNone(confirmed)
        self.assertIsNone(observed)

    def test_expired_audit_recovers_when_its_slot_is_still_ready(self) -> None:
        decision = RotationDecision(
            key="3",
            label="Unstable Bladestorm",
            slot="Weapon_3",
            delay_seconds=0.42,
            reason="test",
            expected_skill_ids=(62607,),
        )
        pending = tasks._PendingRotationAction(
            decision=decision,
            baseline_sequence=0,
            sent_at=100.0,
            deadline=102.5,
        )
        snapshot = CombatTelemetrySnapshot(
            bridge_status="ArcDPS BHud connected",
            character_loaded=True,
            skills=(SkillCooldown(None, "Weapon_3", "Weapon_3", True, 0.0),),
            buffs=(),
        )

        cancelled = tasks._pending_action_looks_cancelled(pending, snapshot)

        self.assertTrue(cancelled)

    def test_expired_weapon_five_audit_ignores_a_weapon_swap(self) -> None:
        decision = RotationDecision(
            key="5",
            label="Phantasmal Swordsman",
            slot="Weapon_5",
            delay_seconds=0.82,
            reason="test",
            expected_skill_ids=(10174,),
        )
        pending = tasks._PendingRotationAction(
            decision=decision,
            baseline_sequence=0,
            sent_at=100.0,
            deadline=102.5,
            weapon_set="sword",
        )
        snapshot = CombatTelemetrySnapshot(
            bridge_status="ArcDPS BHud connected",
            character_loaded=True,
            skills=(SkillCooldown(None, "Weapon_5", "Weapon_5", True, 0.0),),
            buffs=(),
            weapon_set="focus",
        )

        cancelled = tasks._pending_action_looks_cancelled(pending, snapshot)

        self.assertFalse(cancelled)

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
                    skill_activations=(SkillActivation(62510, time.monotonic(), 1),),
                ),
                CombatTelemetrySnapshot(
                    bridge_status="ArcDPS BHud connected",
                    character_loaded=True,
                    skills=(),
                    buffs=(),
                    last_skill_id=62607,
                    skill_activation_sequence=2,
                    last_skill_activated_at=time.monotonic(),
                    skill_activations=(
                        SkillActivation(62510, time.monotonic(), 1),
                        SkillActivation(62607, time.monotonic(), 2),
                    ),
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