from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from gw2helper.automation.condition_virtuoso import (
    ConditionVirtuosoKeybinds,
    ConditionVirtuosoPlanner,
)
from gw2helper.services.arcdps_telemetry import (
    ActiveBuff,
    CombatTelemetrySnapshot,
    SkillCooldown,
)


def _snapshot(
    *,
    skills: tuple[SkillCooldown, ...],
    buffs: tuple[ActiveBuff, ...] = (),
    blades: int = 0,
    cc_bar_visible: bool = False,
    weapon_set: str | None = None,
) -> CombatTelemetrySnapshot:
    return CombatTelemetrySnapshot(
        bridge_status="ArcDPS BHud connected",
        character_loaded=True,
        skills=skills,
        buffs=buffs,
        blade_count=blades,
        cc_bar_visible=cc_bar_visible,
        weapon_set=weapon_set,
    )


def _skill(slot: str, ready: bool = True) -> SkillCooldown:
    return SkillCooldown(None, slot, slot, ready, 0.0 if ready else None)


class ConditionVirtuosoPlannerTests(unittest.TestCase):
    def test_optional_signet_of_illusions_binding_reads_from_environment(self) -> None:
        with patch.dict(
            os.environ,
            {"GW2_CV_SIGNET_ILLUSIONS_KEY": "7"},
            clear=True,
        ):
            keybinds = ConditionVirtuosoKeybinds.from_environment()

        self.assertEqual(keybinds.signet_of_illusions, "7")

    def test_casts_sorrow_at_five_blades_before_other_priority_actions(self) -> None:
        planner = ConditionVirtuosoPlanner(use_opener=False)
        decision = planner.choose(
            _snapshot(
                skills=(_skill("Profession_2"), _skill("Weapon_4")),
                blades=5,
            ),
            100.0,
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.label, "Bladesong Sorrow")
        self.assertEqual(decision.key, "{F2}")

    def test_uses_swordsman_then_swaps_offhand_set(self) -> None:
        planner = ConditionVirtuosoPlanner(use_opener=False)
        initial = _snapshot(
            skills=(_skill("Weapon_5"), _skill("WeaponSwap")),
            buffs=(ActiveBuff(1187, "Quickness", 1, None),),
        )
        swordsman = planner.choose(initial, 100.0)
        self.assertIsNotNone(swordsman)
        self.assertEqual(swordsman.label, "Phantasmal Swordsman")
        self.assertEqual(swordsman.key, "5")
        planner.record_action(swordsman, 100.0)

        swap = planner.choose(initial, 100.9)
        self.assertIsNotNone(swap)
        self.assertEqual(swap.label, "Weapon Swap")
        planner.record_action(swap, 100.9)

        warden = planner.choose(initial, 101.4)
        self.assertIsNotNone(warden)
        self.assertEqual(warden.label, "Phantasmal Warden")

    def test_hud_weapon_set_calibrates_the_initial_phantasm(self) -> None:
        planner = ConditionVirtuosoPlanner(use_opener=False)
        decision = planner.choose(
            _snapshot(
                skills=(_skill("Weapon_5"),),
                weapon_set="focus",
            ),
            100.0,
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.label, "Phantasmal Warden")

    def test_signet_of_ether_waits_for_warden_reset_before_swapping(self) -> None:
        planner = ConditionVirtuosoPlanner(use_opener=False)
        focus_warden = _snapshot(
            skills=(_skill("Weapon_5"), _skill("WeaponSwap")),
            buffs=(ActiveBuff(1187, "Quickness", 1, None),),
            weapon_set="focus",
        )
        warden = planner.choose(focus_warden, 100.0)
        self.assertIsNotNone(warden)
        self.assertEqual(warden.label, "Phantasmal Warden")
        planner.record_action(warden, 100.0)

        signet = planner.choose(
            _snapshot(
                skills=(_skill("Heal"), _skill("WeaponSwap")),
                buffs=(ActiveBuff(1187, "Quickness", 1, None),),
                weapon_set="focus",
            ),
            100.5,
        )
        self.assertIsNotNone(signet)
        self.assertEqual(signet.label, "Signet of the Ether")
        planner.record_action(signet, 100.5)

        waiting = planner.choose(
            _snapshot(
                skills=(_skill("WeaponSwap"),),
                buffs=(ActiveBuff(1187, "Quickness", 1, None),),
                weapon_set="focus",
            ),
            101.0,
        )
        self.assertIsNone(waiting)

        reset_warden = planner.choose(focus_warden, 101.5)
        self.assertIsNotNone(reset_warden)
        self.assertEqual(reset_warden.reason, "Signet of the Ether reset")

    def test_missing_quickness_uses_conservative_input_delay(self) -> None:
        planner = ConditionVirtuosoPlanner(use_opener=False)
        no_quickness = planner.choose(_snapshot(skills=(_skill("Weapon_3"),)), 100.0)
        with_quickness = planner.choose(
            _snapshot(
                skills=(_skill("Weapon_3"),),
                buffs=(ActiveBuff(1187, "Quickness", 1, None),),
            ),
            100.0,
        )

        self.assertIsNotNone(no_quickness)
        self.assertIsNotNone(with_quickness)
        self.assertEqual(no_quickness.label, "Unstable Bladestorm")
        self.assertGreater(no_quickness.delay_seconds, with_quickness.delay_seconds)

    def test_chill_prevents_fast_queueing_even_with_quickness(self) -> None:
        planner = ConditionVirtuosoPlanner(use_opener=False)
        decision = planner.choose(
            _snapshot(
                skills=(_skill("Weapon_3"),),
                buffs=(
                    ActiveBuff(1187, "Quickness", 1, None),
                    ActiveBuff(722, "Chilled", 1, 4.0),
                ),
            ),
            100.0,
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.delay_seconds, 0.525)

    def test_immobilize_uses_conservative_timing(self) -> None:
        planner = ConditionVirtuosoPlanner(use_opener=False)
        decision = planner.choose(
            _snapshot(
                skills=(_skill("Weapon_3"),),
                buffs=(ActiveBuff(727, "Immobilized", 1, 1.0),),
            ),
            100.0,
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.delay_seconds, 0.525)

    def test_hard_control_stops_new_inputs_until_it_clears(self) -> None:
        planner = ConditionVirtuosoPlanner(use_opener=False)
        decision = planner.choose(
            _snapshot(
                skills=(_skill("Weapon_3"),),
                buffs=(ActiveBuff(0, "Daze", 1, 1.0),),
            ),
            100.0,
        )

        self.assertIsNone(decision)

    def test_cc_option_uses_distortion_when_a_breakbar_is_visible(self) -> None:
        planner = ConditionVirtuosoPlanner(use_opener=False)
        decision = planner.choose(
            _snapshot(
                skills=(_skill("Profession_3"), _skill("Weapon_3")),
                cc_bar_visible=True,
            ),
            100.0,
            cc_enabled=True,
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.label, "Bladesong Distortion")

    def test_benchmark_opener_uses_weapon_five_and_profession_five(self) -> None:
        planner = ConditionVirtuosoPlanner()
        ready = _snapshot(
            skills=(
                _skill("Weapon_2"),
                _skill("Weapon_3"),
                _skill("Weapon_5"),
                _skill("WeaponSwap"),
                _skill("Heal"),
                _skill("Elite"),
                _skill("Profession_1"),
                _skill("Profession_2"),
                _skill("Profession_5"),
            ),
            blades=5,
            weapon_set="sword",
        )
        first = planner.choose(ready, 100.0)
        self.assertIsNotNone(first)
        self.assertEqual(first.label, "Phantasmal Swordsman")
        self.assertEqual(first.key, "5")
        self.assertEqual(first.expected_skill_ids, (10174,))

        planner._opener_index = len(planner._OPENER) - 1
        bladeturn = planner.choose(ready, 101.0)
        self.assertIsNotNone(bladeturn)
        self.assertEqual(bladeturn.label, "Bladeturn Requiem")
        self.assertEqual(bladeturn.key, "{F5}")
        self.assertEqual(bladeturn.expected_skill_ids, (62597,))


if __name__ == "__main__":
    unittest.main()