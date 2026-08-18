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
    player_moving: bool = False,
) -> CombatTelemetrySnapshot:
    return CombatTelemetrySnapshot(
        bridge_status="ArcDPS BHud connected",
        character_loaded=True,
        skills=skills,
        buffs=buffs,
        blade_count=blades,
        cc_bar_visible=cc_bar_visible,
        weapon_set=weapon_set,
        player_moving=player_moving,
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

    def test_default_utility_bindings_match_the_live_profile(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            keybinds = ConditionVirtuosoKeybinds.from_environment()

        self.assertEqual(keybinds.signet_of_ether, "b")
        self.assertEqual(keybinds.signet_of_midnight, "q")
        self.assertEqual(keybinds.signet_of_illusions, "e")
        self.assertEqual(keybinds.signet_of_domination, "t")
        self.assertEqual(keybinds.thousand_cuts, "r")

    def test_skips_optional_signet_when_utility_template_is_not_ready(self) -> None:
        planner = ConditionVirtuosoPlanner()
        planner._opener_index = 11
        decision = planner.choose(
            _snapshot(
                skills=(_skill("Utility_Illusions", False), _skill("Profession_2")),
                blades=5,
            ),
            100.0,
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.label, "Bladesong Sorrow")

    def test_opener_uses_e_for_ready_signet_of_illusions(self) -> None:
        planner = ConditionVirtuosoPlanner(
            ConditionVirtuosoKeybinds(signet_of_illusions="e")
        )
        planner._opener_index = 11
        decision = planner.choose(
            _snapshot(
                skills=(_skill("Utility_Illusions"),),
                blades=5,
            ),
            100.0,
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.label, "Signet of Illusions")
        self.assertEqual(decision.key, "e")

    def test_recovers_from_mismatched_optional_signet(self) -> None:
        planner = ConditionVirtuosoPlanner(
            ConditionVirtuosoKeybinds(signet_of_illusions="q")
        )
        planner._opener_index = 11
        snapshot = _snapshot(
            skills=(_skill("Utility_Illusions"), _skill("Profession_2")),
            blades=5,
        )
        signet = planner.choose(snapshot, 100.0)

        self.assertIsNotNone(signet)
        self.assertEqual(signet.label, "Signet of Illusions")
        planner.recover_from_interruption(
            signet,
            snapshot,
            100.1,
            observed_skill_id=10234,
        )

        recovered = planner.choose(snapshot, 100.3)
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.label, "Bladesong Sorrow")

    def test_unrelated_native_activation_does_not_disable_bladecall(self) -> None:
        planner = ConditionVirtuosoPlanner(use_opener=False)
        snapshot = _snapshot(skills=(_skill("Weapon_2"),))
        bladecall = planner.choose(snapshot, 100.0)

        self.assertIsNotNone(bladecall)
        self.assertEqual(bladecall.label, "Bladecall")
        planner.recover_from_interruption(
            bladecall,
            snapshot,
            100.1,
            observed_skill_id=10174,
        )

        recovered = planner.choose(snapshot, 100.3)
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.label, "Bladecall")

    def test_recovers_from_a_blocked_opener_step_without_long_stall(self) -> None:
        planner = ConditionVirtuosoPlanner()
        planner._opener_index = 8
        snapshot = _snapshot(skills=(), blades=0)

        self.assertIsNone(planner.choose(snapshot, 100.0))
        recovered = planner.choose(snapshot, 101.6)

        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.label, "Resume Flying Cutter")

    def test_casts_sorrow_at_five_blades_before_other_priority_actions(self) -> None:
        planner = ConditionVirtuosoPlanner(use_opener=False)
        decision = planner.choose(
            _snapshot(
                skills=(
                    _skill("Profession_1"),
                    _skill("Profession_2"),
                    _skill("Profession_5"),
                ),
                blades=5,
            ),
            100.0,
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.label, "Bladesong Sorrow")
        self.assertEqual(decision.key, "{F2}")

    def test_does_not_spend_blades_before_five_are_available(self) -> None:
        planner = ConditionVirtuosoPlanner(use_opener=False)
        decision = planner.choose(
            _snapshot(
                skills=(
                    _skill("Profession_1"),
                    _skill("Profession_2"),
                    _skill("Profession_3"),
                    _skill("Profession_5"),
                ),
                blades=4,
            ),
            100.0,
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.label, "Maintain Flying Cutter")

    def test_casts_harmony_before_bladeturn_when_sorrow_is_unavailable(self) -> None:
        planner = ConditionVirtuosoPlanner(use_opener=False)
        decision = planner.choose(
            _snapshot(
                skills=(_skill("Profession_1"), _skill("Profession_5")),
                blades=5,
            ),
            100.0,
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.label, "Bladesong Harmony")

    def test_casts_dissonance_before_bladeturn_when_other_bladesongs_are_unavailable(self) -> None:
        planner = ConditionVirtuosoPlanner(use_opener=False)
        decision = planner.choose(
            _snapshot(
                skills=(_skill("Profession_3"), _skill("Profession_5")),
                blades=5,
            ),
            100.0,
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.label, "Bladesong Distortion")

    def test_keeps_sword_set_for_a_second_swordsman_before_swapping(self) -> None:
        planner = ConditionVirtuosoPlanner(use_opener=False)
        quickness = (ActiveBuff(1187, "Quickness", 1, None),)
        sword_ready = _snapshot(
            skills=(_skill("Weapon_5"), _skill("WeaponSwap")),
            buffs=quickness,
            weapon_set="sword",
        )
        first_swordsman = planner.choose(sword_ready, 100.0)

        self.assertIsNotNone(first_swordsman)
        self.assertEqual(first_swordsman.label, "Phantasmal Swordsman")
        planner.record_action(first_swordsman, 100.0)

        still_sword = _snapshot(
            skills=(_skill("WeaponSwap"),),
            buffs=quickness,
            weapon_set="sword",
        )
        interim = planner.choose(still_sword, 100.5)

        self.assertIsNotNone(interim)
        self.assertEqual(interim.label, "Maintain Flying Cutter")
        planner.record_action(interim, 100.5)

        second_swordsman = planner.choose(sword_ready, 101.0)

        self.assertIsNotNone(second_swordsman)
        self.assertEqual(second_swordsman.label, "Phantasmal Swordsman")
        planner.record_action(second_swordsman, 101.0)

        swap = planner.choose(still_sword, 101.5)

        self.assertIsNotNone(swap)
        self.assertEqual(swap.label, "Weapon Swap")

    def test_maintains_autoattack_when_no_priority_action_is_available(self) -> None:
        planner = ConditionVirtuosoPlanner(use_opener=False)
        idle = _snapshot(skills=())

        first = planner.choose(idle, 100.0)

        self.assertIsNotNone(first)
        self.assertEqual(first.label, "Maintain Flying Cutter")
        planner.record_action(first, 100.0)
        self.assertIsNone(planner.choose(idle, 100.3))

        resumed = planner.choose(idle, 100.8)

        self.assertIsNotNone(resumed)
        self.assertEqual(resumed.label, "Maintain Flying Cutter")

    def test_uses_two_swordsmen_then_swaps_offhand_set(self) -> None:
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

        second_swordsman = planner.choose(initial, 100.9)
        self.assertIsNotNone(second_swordsman)
        self.assertEqual(second_swordsman.label, "Phantasmal Swordsman")
        planner.record_action(second_swordsman, 100.9)

        swap = planner.choose(initial, 101.4)
        self.assertIsNotNone(swap)
        self.assertEqual(swap.label, "Weapon Swap")
        planner.record_action(swap, 101.4)

        warden = planner.choose(initial, 101.9)
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

    def test_does_not_revert_a_local_swap_from_stale_hud_weapon_state(self) -> None:
        planner = ConditionVirtuosoPlanner(use_opener=False)
        planner._weapon_set = "focus"
        planner._toggle_weapon_set(100.0)

        decision = planner.choose(
            _snapshot(
                skills=(_skill("Weapon_5"),),
                weapon_set="focus",
            ),
            101.0,
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.label, "Phantasmal Swordsman")

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

    def test_player_movement_stops_new_cast_inputs(self) -> None:
        planner = ConditionVirtuosoPlanner(use_opener=False)
        decision = planner.choose(
            _snapshot(
                skills=(_skill("Weapon_3"),),
                player_moving=True,
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