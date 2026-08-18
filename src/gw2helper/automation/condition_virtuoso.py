"""Adaptive priority planner for the Snow Crows condition Virtuoso build."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from ..services.arcdps_telemetry import CombatTelemetrySnapshot, SkillCooldown

_SKILL_FLYING_CUTTER = 62510
_SKILL_BLADECALL = 62560
_SKILL_UNSTABLE_BLADESTORM = 62607
_SKILL_HARMONY = 62586
_SKILL_SORROW = 62616
_SKILL_DISTORTION = 62602
_SKILL_BLADETURN = 62597
_SKILL_SWORDSMAN = 10174
_SKILL_WARDEN = 10282
_SKILL_SIGNET_ETHER = 21750
_SKILL_SIGNET_ILLUSIONS = 10247
_SKILL_THOUSAND_CUTS = 24755


@dataclass(frozen=True)
class ConditionVirtuosoKeybinds:
    """Bindings used by the existing Guild Wars 2 helper profile."""

    weapon_2: str = "2"
    weapon_3: str = "3"
    weapon_5: str = "5"
    swordsman: str = "5"
    warden: str = "5"
    harmony: str = "{F1}"
    sorrow: str = "{F2}"
    distortion: str = "{F3}"
    bladeturn: str = "{F5}"
    signet_of_ether: str = "b"
    signet_of_midnight: str = "q"
    signet_of_domination: str = "t"
    thousand_cuts: str = "r"
    weapon_swap: str = "°"
    auto_attack: str = "1"
    signet_of_illusions: Optional[str] = "e"

    @classmethod
    def from_environment(cls) -> "ConditionVirtuosoKeybinds":
        """Load local bindings while retaining the benchmark action defaults."""

        weapon_5 = _configured_key(
            "GW2_CV_WEAPON_5_KEY",
            _configured_key("GW2_CV_OFFHAND_5_KEY", "5"),
        )
        return cls(
            weapon_2=_configured_key("GW2_CV_WEAPON_2_KEY", "2"),
            weapon_3=_configured_key("GW2_CV_WEAPON_3_KEY", "3"),
            weapon_5=weapon_5,
            swordsman=_configured_key("GW2_CV_SWORDSMAN_KEY", weapon_5),
            warden=_configured_key("GW2_CV_WARDEN_KEY", weapon_5),
            harmony=_configured_key("GW2_CV_HARMONY_KEY", "{F1}"),
            sorrow=_configured_key("GW2_CV_SORROW_KEY", "{F2}"),
            distortion=_configured_key("GW2_CV_DISTORTION_KEY", "{F3}"),
            bladeturn=_configured_key("GW2_CV_BLADETURN_KEY", "{F5}"),
            signet_of_ether=_configured_key("GW2_CV_SIGNET_ETHER_KEY", "b"),
            signet_of_midnight=_configured_key("GW2_CV_SIGNET_MIDNIGHT_KEY", "q"),
            signet_of_domination=_configured_key("GW2_CV_SIGNET_DOMINATION_KEY", "t"),
            thousand_cuts=_configured_key("GW2_CV_THOUSAND_CUTS_KEY", "r"),
            weapon_swap=_configured_key("GW2_CV_WEAPON_SWAP_KEY", "°"),
            auto_attack=_configured_key("GW2_CV_AUTO_ATTACK_KEY", "1"),
            signet_of_illusions=_configured_optional_key(
                "GW2_CV_SIGNET_ILLUSIONS_KEY",
                "e",
            ),
        )


@dataclass(frozen=True)
class RotationDecision:
    key: str
    label: str
    slot: Optional[str]
    delay_seconds: float
    reason: str
    expected_skill_ids: tuple[int, ...] = ()
    opener_step: Optional[int] = None


@dataclass(frozen=True)
class _OpenerStep:
    label: str
    key_attribute: str
    slot: Optional[str]
    expected_skill_ids: tuple[int, ...]
    base_delay_seconds: float
    reason: str
    required_blades: int = 0
    optional: bool = False


class ConditionVirtuosoPlanner:
    """Choose the next safe action from current skill, blade, and buff state."""

    _SAME_SLOT_GUARD_SECONDS = 0.45
    _AUTO_ATTACK_GUARD_SECONDS = 0.75
    _SWORDSMEN_PER_SWORD_SET = 2
    _SIGNET_ILLUSIONS_GUARD_SECONDS = 45.0
    _WARDEN_RESET_WAIT_SECONDS = 1.0
    _OPENER_TIMEOUT_SECONDS = 20.0
    _OPENER_STEP_TIMEOUT_SECONDS = 1.5
    _HARD_CONTROL_EFFECTS = {
        "daze",
        "fear",
        "knockdown",
        "stun",
        "taunt",
    }
    _TIMING_DEBUFFS = {"chilled", "slow", "immobilized"}

    _OPENER = (
        _OpenerStep(
            "Phantasmal Swordsman", "swordsman", "Weapon_5", (_SKILL_SWORDSMAN,), 0.82, "benchmark opener"
        ),
        _OpenerStep(
            "Weapon Swap", "weapon_swap", "WeaponSwap", (), 0.20, "benchmark opener"
        ),
        _OpenerStep(
            "Bladecall", "weapon_2", "Weapon_2", (_SKILL_BLADECALL,), 0.44, "benchmark opener"
        ),
        _OpenerStep(
            "Phantasmal Warden", "warden", "Weapon_5", (_SKILL_WARDEN,), 0.45, "benchmark opener"
        ),
        _OpenerStep(
            "Signet of the Ether", "signet_of_ether", "Heal", (_SKILL_SIGNET_ETHER,), 0.90, "reset Phantasmal Warden"
        ),
        _OpenerStep(
            "Bladesong Harmony", "harmony", "Profession_1", (_SKILL_HARMONY,), 0.64, "benchmark opener"
        ),
        _OpenerStep(
            "Phantasmal Warden", "warden", "Weapon_5", (_SKILL_WARDEN,), 0.45, "Signet of the Ether reset"
        ),
        _OpenerStep(
            "Thousand Cuts", "thousand_cuts", "Elite", (_SKILL_THOUSAND_CUTS,), 0.12, "benchmark opener"
        ),
        _OpenerStep(
            "Bladesong Sorrow", "sorrow", "Profession_2", (_SKILL_SORROW,), 0.48, "five blades", required_blades=5
        ),
        _OpenerStep(
            "Bladesong Harmony", "harmony", "Profession_1", (_SKILL_HARMONY,), 0.64, "benchmark opener"
        ),
        _OpenerStep(
            "Bladecall", "weapon_2", "Weapon_2", (_SKILL_BLADECALL,), 0.44, "benchmark opener"
        ),
        _OpenerStep(
            "Signet of Illusions", "signet_of_illusions", "Utility_Illusions", (_SKILL_SIGNET_ILLUSIONS,), 0.12, "reset Bladesongs", optional=True
        ),
        _OpenerStep(
            "Bladesong Sorrow", "sorrow", "Profession_2", (_SKILL_SORROW,), 0.48, "five blades", required_blades=5
        ),
        _OpenerStep(
            "Bladesong Harmony", "harmony", "Profession_1", (_SKILL_HARMONY,), 0.64, "benchmark opener"
        ),
        _OpenerStep(
            "Unstable Bladestorm", "weapon_3", "Weapon_3", (_SKILL_UNSTABLE_BLADESTORM,), 0.44, "benchmark opener"
        ),
        _OpenerStep(
            "Bladecall", "weapon_2", "Weapon_2", (_SKILL_BLADECALL,), 0.44, "benchmark opener"
        ),
        _OpenerStep(
            "Weapon Swap", "weapon_swap", "WeaponSwap", (), 0.20, "benchmark opener"
        ),
        _OpenerStep(
            "Phantasmal Swordsman", "swordsman", "Weapon_5", (_SKILL_SWORDSMAN,), 0.82, "benchmark opener"
        ),
        _OpenerStep(
            "Bladeturn Requiem", "bladeturn", "Profession_5", (_SKILL_BLADETURN,), 0.15, "five blades", required_blades=5
        ),
    )

    def __init__(
        self,
        keybinds: Optional[ConditionVirtuosoKeybinds] = None,
        *,
        use_opener: bool = True,
    ) -> None:
        self._keybinds = keybinds or ConditionVirtuosoKeybinds.from_environment()
        self._weapon_set = "sword"
        self._pending_weapon_swap = False
        self._pending_signet_reset = False
        self._focus_warden_reset_used = False
        self._awaiting_warden_reset_until = 0.0
        self._next_action_at = 0.0
        self._weapon_set_calibrated = False
        self._slot_blocked_until: dict[str, float] = {}
        self._last_signet_illusions_at = float("-inf")
        self._disabled_skill_ids: set[int] = set()
        self._resume_auto_attack = False
        self._last_auto_attack_at = float("-inf")
        self._swordsmen_since_swap = 0
        self._opener_index = 0
        self._opener_complete = not use_opener
        self._opener_started_at: Optional[float] = None
        self._opener_step_wait_started_at: Optional[float] = None

    def choose(
        self,
        snapshot: CombatTelemetrySnapshot,
        now: float,
        *,
        cc_enabled: bool = False,
    ) -> Optional[RotationDecision]:
        """Return the highest-priority legal action, or ``None`` while waiting."""

        if snapshot.bridge_status != "ArcDPS BHud connected":
            return None
        if snapshot.character_loaded is not True or now < self._next_action_at:
            return None
        if snapshot.player_moving:
            return None

        if (
            not self._weapon_set_calibrated
            and snapshot.weapon_set in {"focus", "sword"}
        ):
            self._weapon_set = snapshot.weapon_set
            self._weapon_set_calibrated = True

        buff_names = {buff.name.casefold() for buff in snapshot.buffs}
        if self._HARD_CONTROL_EFFECTS & buff_names:
            return None

        readiness = {skill.slot: skill.ready for skill in snapshot.skills if skill.slot}
        if not self._opener_complete:
            opener_decision = self._choose_opener(
                snapshot,
                readiness,
                buff_names,
                now,
            )
            if opener_decision is not None:
                return opener_decision
            if self._opener_complete:
                pass
            elif (
                self._opener_started_at is not None
                and now - self._opener_started_at >= self._OPENER_TIMEOUT_SECONDS
            ):
                self._opener_complete = True
            else:
                return None
        timing_delay = self._timing_delay(buff_names)

        if (
            cc_enabled
            and snapshot.cc_bar_visible
            and self._ready(readiness, "Profession_3", now)
            and self._is_enabled((_SKILL_DISTORTION,))
        ):
            return self._decision(
                self._keybinds.distortion,
                "Bladesong Distortion",
                "Profession_3",
                timing_delay,
                "breakbar visible",
                expected_skill_ids=(_SKILL_DISTORTION,),
            )

        if snapshot.blade_count >= 5:
            if self._ready(readiness, "Profession_2", now) and self._is_enabled(
                (_SKILL_SORROW,)
            ):
                return self._decision(
                    self._keybinds.sorrow,
                    "Bladesong Sorrow",
                    "Profession_2",
                    timing_delay,
                    "five blades",
                    expected_skill_ids=(_SKILL_SORROW,),
                )
            if self._ready(readiness, "Profession_1", now) and self._is_enabled(
                (_SKILL_HARMONY,)
            ):
                return self._decision(
                    self._keybinds.harmony,
                    "Bladesong Harmony",
                    "Profession_1",
                    timing_delay,
                    "five blades",
                    expected_skill_ids=(_SKILL_HARMONY,),
                )
            if self._ready(readiness, "Profession_3", now) and self._is_enabled(
                (_SKILL_DISTORTION,)
            ):
                return self._decision(
                    self._keybinds.distortion,
                    "Bladesong Distortion",
                    "Profession_3",
                    timing_delay,
                    "five blades after Bladesongs",
                    expected_skill_ids=(_SKILL_DISTORTION,),
                )
            if self._ready(readiness, "Profession_5", now) and self._is_enabled(
                (_SKILL_BLADETURN,)
            ):
                return self._decision(
                    self._keybinds.bladeturn,
                    "Bladeturn Requiem",
                    "Profession_5",
                    timing_delay,
                    "five blades after Bladesongs",
                    expected_skill_ids=(_SKILL_BLADETURN,),
                )

        if self._weapon_set == "focus" and self._pending_signet_reset:
            if self._ready(readiness, "Heal", now) and self._is_enabled(
                (_SKILL_SIGNET_ETHER,)
            ):
                return self._decision(
                    self._keybinds.signet_of_ether,
                    "Signet of the Ether",
                    "Heal",
                    timing_delay,
                    "reset Phantasmal Warden",
                    expected_skill_ids=(_SKILL_SIGNET_ETHER,),
                )
            self._pending_signet_reset = False
            self._pending_weapon_swap = True

        if self._weapon_set == "focus" and self._awaiting_warden_reset_until:
            if self._ready(readiness, "Weapon_5", now) and self._is_enabled(
                (_SKILL_WARDEN,)
            ):
                return self._decision(
                    self._keybinds.warden,
                    "Phantasmal Warden",
                    "Weapon_5",
                    timing_delay,
                    "Signet of the Ether reset",
                    expected_skill_ids=(_SKILL_WARDEN,),
                )
            if now < self._awaiting_warden_reset_until:
                return None
            self._awaiting_warden_reset_until = 0.0
            self._pending_weapon_swap = True

        if self._pending_weapon_swap and self._ready(readiness, "WeaponSwap", now):
            return self._decision(
                self._keybinds.weapon_swap,
                "Weapon Swap",
                "WeaponSwap",
                timing_delay,
                "off-hand phantasm complete",
            )

        if (
            self._weapon_set == "sword"
            and self._ready(readiness, "Weapon_5", now)
            and self._is_enabled((_SKILL_SWORDSMAN,))
        ):
            return self._decision(
                self._keybinds.swordsman,
                "Phantasmal Swordsman",
                "Weapon_5",
                timing_delay,
                "sword priority",
                expected_skill_ids=(_SKILL_SWORDSMAN,),
            )

        if (
            self._weapon_set == "focus"
            and self._ready(readiness, "Weapon_5", now)
            and self._is_enabled((_SKILL_WARDEN,))
        ):
            return self._decision(
                self._keybinds.warden,
                "Phantasmal Warden",
                "Weapon_5",
                timing_delay,
                "focus priority",
                expected_skill_ids=(_SKILL_WARDEN,),
            )

        if self._ready(readiness, "Elite", now) and self._is_enabled(
            (_SKILL_THOUSAND_CUTS,)
        ):
            return self._decision(
                self._keybinds.thousand_cuts,
                "Thousand Cuts",
                "Elite",
                timing_delay,
                "elite off cooldown",
                expected_skill_ids=(_SKILL_THOUSAND_CUTS,),
            )

        if self._ready(readiness, "Weapon_3", now) and self._is_enabled(
            (_SKILL_UNSTABLE_BLADESTORM,)
        ):
            return self._decision(
                self._keybinds.weapon_3,
                "Unstable Bladestorm",
                "Weapon_3",
                timing_delay,
                "off cooldown",
                expected_skill_ids=(_SKILL_UNSTABLE_BLADESTORM,),
            )

        if self._ready(readiness, "Weapon_2", now) and self._is_enabled(
            (_SKILL_BLADECALL,)
        ):
            return self._decision(
                self._keybinds.weapon_2,
                "Bladecall",
                "Weapon_2",
                timing_delay,
                "off cooldown",
                expected_skill_ids=(_SKILL_BLADECALL,),
            )

        if self._can_use_signet_of_illusions(readiness, now):
            return self._decision(
                self._keybinds.signet_of_illusions or "",
                "Signet of Illusions",
                "Utility_Illusions",
                timing_delay,
                "Bladesongs unavailable",
                expected_skill_ids=(_SKILL_SIGNET_ILLUSIONS,),
            )

        if self._pending_weapon_swap and self._ready(readiness, "WeaponSwap", now):
            return self._decision(
                self._keybinds.weapon_swap,
                "Weapon Swap",
                "WeaponSwap",
                timing_delay,
                "continue weapon loop",
            )

        if self._resume_auto_attack:
            return self._decision(
                self._keybinds.auto_attack,
                "Resume Flying Cutter",
                None,
                min(timing_delay, 0.20),
                "recover after interrupted cast",
            )

        if now - self._last_auto_attack_at >= self._AUTO_ATTACK_GUARD_SECONDS:
            return self._decision(
                self._keybinds.auto_attack,
                "Maintain Flying Cutter",
                None,
                min(timing_delay, 0.20),
                "no priority action ready",
            )

        return None

    def record_action(self, decision: RotationDecision, now: float) -> None:
        """Advance local loop state only after the input was sent successfully."""

        self._next_action_at = now + decision.delay_seconds
        if decision.slot:
            self._slot_blocked_until[decision.slot] = max(
                self._slot_blocked_until.get(decision.slot, 0.0),
                now + self._SAME_SLOT_GUARD_SECONDS,
            )

        if decision.opener_step is not None:
            self._opener_step_wait_started_at = None
            if decision.slot == "WeaponSwap":
                self._toggle_weapon_set(now)
            if decision.opener_step == self._opener_index:
                self._opener_index += 1
            if self._opener_index >= len(self._OPENER):
                self._opener_complete = True
                self._pending_weapon_swap = self._weapon_set == "sword"
            return

        if decision.label == "Phantasmal Swordsman":
            self._swordsmen_since_swap += 1
            self._pending_weapon_swap = (
                self._swordsmen_since_swap >= self._SWORDSMEN_PER_SWORD_SET
            )
        elif decision.label == "Phantasmal Warden":
            if self._focus_warden_reset_used:
                self._pending_weapon_swap = True
            else:
                self._pending_signet_reset = True
        elif decision.slot == "Heal":
            self._pending_signet_reset = False
            self._focus_warden_reset_used = True
            self._awaiting_warden_reset_until = now + self._WARDEN_RESET_WAIT_SECONDS
        elif decision.slot == "WeaponSwap":
            self._toggle_weapon_set(now)
        elif decision.label == "Signet of Illusions":
            self._last_signet_illusions_at = now
        elif decision.label in {"Resume Flying Cutter", "Maintain Flying Cutter"}:
            self._resume_auto_attack = False
            self._last_auto_attack_at = now

    def recover_from_interruption(
        self,
        decision: RotationDecision,
        snapshot: CombatTelemetrySnapshot,
        now: float,
        *,
        observed_skill_id: Optional[int] = None,
    ) -> None:
        """Return to live priority decisions after a cancelled or mismatched input."""

        del observed_skill_id
        if decision.opener_step is not None:
            self._opener_complete = True
        if snapshot.weapon_set in {"focus", "sword"}:
            self._weapon_set = snapshot.weapon_set
            self._weapon_set_calibrated = True
        self._pending_weapon_swap = False
        self._pending_signet_reset = False
        self._awaiting_warden_reset_until = 0.0
        self._slot_blocked_until.clear()
        self._next_action_at = now + 0.15
        self._resume_auto_attack = True

    def disable_binding(
        self,
        decision: RotationDecision,
        snapshot: CombatTelemetrySnapshot,
        now: float,
    ) -> None:
        """Stop retrying one action after ArcDPS proves its physical key is wrong."""

        self._disabled_skill_ids.update(decision.expected_skill_ids)
        self.recover_from_interruption(decision, snapshot, now)

    def _choose_opener(
        self,
        snapshot: CombatTelemetrySnapshot,
        readiness: dict[Optional[str], Optional[bool]],
        buff_names: set[str],
        now: float,
    ) -> Optional[RotationDecision]:
        if self._opener_started_at is None:
            self._opener_started_at = now

        if self._opener_index == 0 and self._weapon_set != "sword":
            if not self._ready(readiness, "WeaponSwap", now):
                return self._wait_or_recover_opener(now)
            return self._decision(
                self._keybinds.weapon_swap,
                "Weapon Swap",
                "WeaponSwap",
                self._scaled_delay(0.20, buff_names),
                "move to Sword set for opener",
            )

        while self._opener_index < len(self._OPENER):
            step = self._OPENER[self._opener_index]
            if step.expected_skill_ids and not self._is_enabled(step.expected_skill_ids):
                self._opener_complete = True
                return None
            key = getattr(self._keybinds, step.key_attribute)
            if step.optional and not key:
                self._opener_index += 1
                continue
            if step.required_blades and snapshot.blade_count < step.required_blades:
                return self._wait_or_recover_opener(now)
            if step.slot and not self._ready(readiness, step.slot, now):
                if step.optional:
                    self._opener_index += 1
                    continue
                return self._wait_or_recover_opener(now)
            self._opener_step_wait_started_at = None
            return self._decision(
                str(key),
                step.label,
                step.slot,
                self._scaled_delay(step.base_delay_seconds, buff_names),
                step.reason,
                expected_skill_ids=step.expected_skill_ids,
                opener_step=self._opener_index,
            )

        self._opener_complete = True
        return None

    def _wait_or_recover_opener(self, now: float) -> Optional[RotationDecision]:
        if self._opener_step_wait_started_at is None:
            self._opener_step_wait_started_at = now
            return None
        if now - self._opener_step_wait_started_at < self._OPENER_STEP_TIMEOUT_SECONDS:
            return None
        self._opener_complete = True
        self._resume_auto_attack = True
        self._opener_step_wait_started_at = None
        return None

    def _toggle_weapon_set(self, now: float) -> None:
        del now
        self._weapon_set = "focus" if self._weapon_set == "sword" else "sword"
        self._weapon_set_calibrated = True
        self._swordsmen_since_swap = 0
        self._pending_weapon_swap = False
        self._pending_signet_reset = False
        self._focus_warden_reset_used = False
        self._awaiting_warden_reset_until = 0.0

    def _can_use_signet_of_illusions(
        self,
        readiness: dict[Optional[str], Optional[bool]],
        now: float,
    ) -> bool:
        return bool(
            self._keybinds.signet_of_illusions
            and self._is_enabled((_SKILL_SIGNET_ILLUSIONS,))
            and now - self._last_signet_illusions_at >= self._SIGNET_ILLUSIONS_GUARD_SECONDS
            and self._ready(readiness, "Utility_Illusions", now)
            and not self._ready(readiness, "Profession_1", now)
            and not self._ready(readiness, "Profession_2", now)
        )

    def _is_enabled(self, expected_skill_ids: tuple[int, ...]) -> bool:
        return not any(
            skill_id in self._disabled_skill_ids for skill_id in expected_skill_ids
        )

    def _ready(
        self,
        readiness: dict[Optional[str], Optional[bool]],
        slot: str,
        now: float,
    ) -> bool:
        return bool(readiness.get(slot) is True and now >= self._slot_blocked_until.get(slot, 0.0))

    def _timing_delay(self, buff_names: set[str]) -> float:
        return self._scaled_delay(0.42, buff_names)

    @staticmethod
    def _timing_multiplier(buff_names: set[str]) -> float:
        if "slow" in buff_names:
            return 1.67
        if "chilled" in buff_names or "immobilized" in buff_names:
            return 1.25
        if "quickness" not in buff_names:
            return 1.45
        return 1.0

    def _scaled_delay(self, base_delay_seconds: float, buff_names: set[str]) -> float:
        return base_delay_seconds * self._timing_multiplier(buff_names)

    def _decision(
        self,
        key: str,
        label: str,
        slot: Optional[str],
        delay_seconds: float,
        reason: str,
        *,
        expected_skill_ids: tuple[int, ...] = (),
        opener_step: Optional[int] = None,
    ) -> RotationDecision:
        return RotationDecision(
            key=key,
            label=label,
            slot=slot,
            delay_seconds=delay_seconds,
            reason=reason,
            expected_skill_ids=expected_skill_ids,
            opener_step=opener_step,
        )


def _configured_key(environment_name: str, default: str) -> str:
    configured = os.getenv(environment_name, "").strip()
    return configured or default


def _configured_optional_key(
    environment_name: str,
    default: Optional[str] = None,
) -> Optional[str]:
    if environment_name not in os.environ:
        return default
    configured = os.getenv(environment_name, "").strip()
    return configured or None