from __future__ import annotations

import struct
import unittest

from gw2helper.services.arcdps_telemetry import (
    ActiveBuff,
    ArcDpsCombatMonitor,
    BHudProtocolError,
    SkillActivation,
    bhud_port_for_pid,
    decode_bhud_payload,
)
from gw2helper.services import arcdps_telemetry
from gw2helper.services.gw2_api import SkillMetadata


def _unsigned(value: int) -> bytes:
    if value < 251:
        return bytes([value])
    if value <= 0xFFFF:
        return b"\xfb" + struct.pack("<H", value)
    if value <= 0xFFFF_FFFF:
        return b"\xfc" + struct.pack("<I", value)
    return b"\xfd" + struct.pack("<Q", value)


def _signed(value: int) -> bytes:
    return _unsigned((value << 1) if value >= 0 else ((-value << 1) - 1))


def _option(value: bool) -> bytes:
    return b"\x01" if value else b"\x00"


def _string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return _unsigned(len(encoded)) + encoded


def _agent(*, agent_id: int, is_self: bool, name: str = "") -> bytes:
    return (
        _option(True)
        + _option(bool(name))
        + (_string(name) if name else b"")
        + _unsigned(agent_id)
        + _unsigned(7)
        + _unsigned(66)
        + _unsigned(1 if is_self else 0)
        + _unsigned(0)
    )


def _combat_payload(
    *,
    statechange: int,
    source_agent: int,
    destination_agent: int,
    skill_id: int,
    value: int,
    overstack_value: int = 0,
    event_time_ms: int = 1_000_000,
    source_is_self: bool = False,
    destination_is_self: bool = False,
    track_id: int = 0,
    skill_name: str = "",
) -> bytes:
    flags = [0] * 16
    flags[8] = statechange
    flags[12] = track_id & 0xFF
    flags[13] = (track_id >> 8) & 0xFF
    flags[14] = (track_id >> 16) & 0xFF
    flags[15] = (track_id >> 24) & 0xFF
    event = (
        _option(True)
        + _unsigned(event_time_ms)
        + _unsigned(source_agent)
        + _unsigned(destination_agent)
        + _signed(value)
        + _signed(0)
        + _unsigned(overstack_value)
        + _unsigned(skill_id)
        + _unsigned(0) * 4
        + bytes(flags)
    )
    return (
        b"\x02"
        + event
        + _agent(agent_id=source_agent, is_self=source_is_self)
        + _agent(agent_id=destination_agent, is_self=destination_is_self)
        + _option(bool(skill_name))
        + (_string(skill_name) if skill_name else b"")
        + _unsigned(1)
        + _unsigned(1)
    )


class _Clock:
    def __init__(self, value: float) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


class ArcDpsTelemetryTests(unittest.TestCase):
    def test_hud_poll_interval_is_shorter_than_a_quickness_cast_window(self) -> None:
        self.assertEqual(arcdps_telemetry._HUD_SCAN_SECONDS, 0.30)

    def test_port_uses_bhud_v2_pid_plus_one_formula(self) -> None:
        self.assertEqual(bhud_port_for_pid(10828), 59981)

    def test_decodes_live_style_ui_frame(self) -> None:
        ui_state, combat = decode_bhud_payload(b"\x01\x01")

        self.assertTrue(ui_state)
        self.assertIsNone(combat)

    def test_rejects_an_invalid_bhud_payload(self) -> None:
        with self.assertRaises(BHudProtocolError):
            decode_bhud_payload(b"\x01\x02")

    def test_tracks_native_buff_apply_and_removal_for_self(self) -> None:
        clock = _Clock(1_000.0)
        monitor = ArcDpsCombatMonitor(clock=clock)
        monitor.ingest_payload(
            _combat_payload(
                statechange=69,
                source_agent=5,
                destination_agent=42,
                destination_is_self=True,
                skill_id=1187,
                value=10_000,
                event_time_ms=1_000_000,
                track_id=99,
                skill_name="Quickness",
            )
        )

        snapshot = monitor.snapshot()
        self.assertEqual(len(snapshot.buffs), 1)
        self.assertEqual(snapshot.buffs[0].name, "Quickness")
        self.assertEqual(snapshot.buffs[0].stacks, 1)
        self.assertEqual(snapshot.buffs[0].remaining_seconds, 10.0)

        monitor.ingest_payload(
            _combat_payload(
                statechange=72,
                source_agent=42,
                destination_agent=5,
                source_is_self=True,
                skill_id=1187,
                value=0,
                event_time_ms=1_001_000,
            )
        )
        self.assertEqual(monitor.snapshot().buffs, ())

    def test_enemy_buff_removal_does_not_clear_the_players_buff(self) -> None:
        clock = _Clock(1_000.0)
        monitor = ArcDpsCombatMonitor(clock=clock)
        monitor.ingest_payload(
            _combat_payload(
                statechange=69,
                source_agent=5,
                destination_agent=42,
                destination_is_self=True,
                skill_id=1187,
                value=10_000,
                event_time_ms=1_000_000,
                track_id=99,
                skill_name="Quickness",
            )
        )
        monitor.ingest_payload(
            _combat_payload(
                statechange=72,
                source_agent=5,
                destination_agent=6,
                skill_id=1187,
                value=0,
                event_time_ms=1_001_000,
            )
        )

        self.assertEqual(monitor.snapshot().buffs[0].name, "Quickness")

    def test_tracks_cooldown_from_native_skill_activation(self) -> None:
        clock = _Clock(1_000.0)
        metadata = SkillMetadata(14375, "Arcing Slice", "Profession_1", 8.0)
        monitor = ArcDpsCombatMonitor(
            skill_lookup=lambda _skill_id: metadata,
            clock=clock,
            asynchronous_skill_lookup=False,
        )
        monitor.ingest_payload(
            _combat_payload(
                statechange=67,
                source_agent=42,
                destination_agent=5,
                source_is_self=True,
                skill_id=14375,
                value=0,
                event_time_ms=1_000_000,
            )
        )

        clock.value = 1_002.0
        snapshot = monitor.snapshot()
        skill = next(skill for skill in snapshot.skills if skill.skill_id == 14375)
        self.assertEqual(skill.name, "Arcing Slice")
        self.assertAlmostEqual(skill.remaining_seconds or 0.0, 6.0)
        self.assertFalse(skill.ready)
        self.assertEqual(snapshot.last_skill_id, 14375)
        self.assertEqual(snapshot.skill_activation_sequence, 1)
        self.assertEqual(snapshot.last_skill_activated_at, 1000.0)
        self.assertEqual(
            snapshot.skill_activations,
            (
                SkillActivation(
                    skill_id=14375,
                    activated_at=1000.0,
                    sequence=1,
                ),
            ),
        )

    def test_ignores_stale_bhud_backlog_events(self) -> None:
        clock = _Clock(1_000.0)
        monitor = ArcDpsCombatMonitor(clock=clock)
        monitor.ingest_payload(
            _combat_payload(
                statechange=69,
                source_agent=5,
                destination_agent=42,
                destination_is_self=True,
                skill_id=1187,
                value=10_000,
                event_time_ms=900_000,
                track_id=99,
                skill_name="Quickness",
            )
        )

        self.assertEqual(monitor.snapshot().buffs, ())

    def test_visual_quickness_is_available_before_native_buff_events(self) -> None:
        monitor = ArcDpsCombatMonitor(clock=_Clock(1_000.0))
        monitor.update_hud_status(
            {
                "Weapon_2": True,
                "buff:Quickness": True,
                "buff:Alacrity": True,
                "resource:blades": 5,
                "target:cc_bar": True,
                "weapon_set:sword": True,
            }
        )

        snapshot = monitor.snapshot()

        self.assertEqual(snapshot.skills[0].name, "Weapon 2")
        self.assertEqual(
            snapshot.buffs,
            (
                ActiveBuff(30328, "Alacrity", 1, None),
                ActiveBuff(1187, "Quickness", 1, None),
            ),
        )
        self.assertEqual(snapshot.blade_count, 5)
        self.assertTrue(snapshot.cc_bar_visible)
        self.assertEqual(snapshot.weapon_set, "sword")

    def test_motion_supplier_is_exposed_in_the_combat_snapshot(self) -> None:
        monitor = ArcDpsCombatMonitor(movement_supplier=lambda: True)

        monitor._refresh_player_movement()

        self.assertTrue(monitor.snapshot().player_moving)


if __name__ == "__main__":
    unittest.main()