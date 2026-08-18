"""Adaptive priority planner for the Snow Crows condition Virtuoso build."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from ..services.arcdps_telemetry import CombatTelemetrySnapshot, SkillCooldown


@dataclass(frozen=True)
class ConditionVirtuosoKeybinds:
    """Bindings used by the existing Guild Wars 2 helper profile."""

    weapon_2: str = "2"
    weapon_3: str = "3"
    offhand_4: str = "4"
    offhand_5: str = "5"
    harmony: str = "{F1}"
    sorrow: str = "{F2}"
    distortion: str = "{F3}"
    signet_of_ether: str = "b"
    thousand_cuts: str = "r"
    weapon_swap: str = "°"
    auto_attack: str = "1"
    signet_of_illusions: Optional[str] = None

    @classmethod
    def from_environment(cls) -> "ConditionVirtuosoKeybinds":
        """Load optional bindings without guessing a player's utility key."""

        return cls(
            weapon_2=_configured_key("GW2_CV_WEAPON_2_KEY", "2"),
            weapon_3=_configured_key("GW2_CV_WEAPON_3_KEY", "3"),
            offhand_4=_configured_key("GW2_CV_OFFHAND_4_KEY", "4"),
            offhand_5=_configured_key("GW2_CV_OFFHAND_5_KEY", "5"),
            harmony=_configured_key("GW2_CV_HARMONY_KEY", "{F1}"),
            sorrow=_configured_key("GW2_CV_SORROW_KEY", "{F2}"),
            distortion=_configured_key("GW2_CV_DISTORTION_KEY", "{F3}"),
            signet_of_ether=_configured_key("GW2_CV_SIGNET_ETHER_KEY", "b"),
            thousand_cuts=_configured_key("GW2_CV_THOUSAND_CUTS_KEY", "r"),
            weapon_swap=_configured_key("GW2_CV_WEAPON_SWAP_KEY", "°"),
            auto_attack=_configured_key("GW2_CV_AUTO_ATTACK_KEY", "1"),
            signet_of_illusions=_configured_optional_key(
                "GW2_CV_SIGNET_ILLUSIONS_KEY"
            ),
        )


@dataclass(frozen=True)
class RotationDecision:
    key: str
    label: str
    slot: Optional[str]
    delay_seconds: float
    reason: str


class ConditionVirtuosoPlanner:
    """Choose the next safe action from current skill, blade, and buff state."""

    _SAME_SLOT_GUARD_SECONDS = 0.38
    _SIGNET_ILLUSIONS_GUARD_SECONDS = 45.0
    _WARDEN_RESET_WAIT_SECONDS = 1.0
    _HARD_CONTROL_EFFECTS = {
        "daze",
        "fear",
        "knockdown",
        "stun",
        "taunt",
    }
    _TIMING_DEBUFFS = {"chilled", "slow", "immobilized"}

    def __init__(self, keybinds: Optional[ConditionVirtuosoKeybinds] = None) -> None:
        self._keybinds = keybinds or ConditionVirtuosoKeybinds.from_environment()
        self._weapon_set = "sword"
        self._pending_weapon_swap = False
        self._pending_signet_reset = False
        self._focus_warden_reset_used = False
        self._awaiting_warden_reset_until = 0.0
        self._next_action_at = 0.0
        self._ignore_hud_weapon_set_until = 0.0
        self._slot_blocked_until: dict[str, float] = {}
        self._last_signet_illusions_at = float("-inf")

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

        if snapshot.weapon_set in {"focus", "sword"} and now >= self._ignore_hud_weapon_set_until:
            self._weapon_set = snapshot.weapon_set

        buff_names = {buff.name.casefold() for buff in snapshot.buffs}
        if self._HARD_CONTROL_EFFECTS & buff_names:
            return None

        readiness = {skill.slot: skill.ready for skill in snapshot.skills if skill.slot}
        timing_delay = self._timing_delay(buff_names)

        if (
            cc_enabled
            and snapshot.cc_bar_visible
            and self._ready(readiness, "Profession_3", now)
        ):
            return self._decision(
                self._keybinds.distortion,
                "Bladesong Distortion",
                "Profession_3",
                timing_delay,
                "breakbar visible",
            )

        if snapshot.blade_count >= 5:
            if self._ready(readiness, "Profession_2", now):
                return self._decision(
                    self._keybinds.sorrow,
                    "Bladesong Sorrow",
                    "Profession_2",
                    timing_delay,
                    "five blades",
                )
            if self._ready(readiness, "Profession_1", now):
                return self._decision(
                    self._keybinds.harmony,
                    "Bladesong Harmony",
                    "Profession_1",
                    timing_delay,
                    "five blades",
                )

        if self._weapon_set == "focus" and self._pending_signet_reset:
            if self._ready(readiness, "Heal", now):
                return self._decision(
                    self._keybinds.signet_of_ether,
                    "Signet of the Ether",
                    "Heal",
                    timing_delay,
                    "reset Phantasmal Warden",
                )
            self._pending_signet_reset = False
            self._pending_weapon_swap = True

        if self._weapon_set == "focus" and self._awaiting_warden_reset_until:
            if self._ready(readiness, "Weapon_4", now):
                return self._decision(
                    self._keybinds.offhand_4,
                    "Phantasmal Warden",
                    "Weapon_4",
                    timing_delay,
                    "Signet of the Ether reset",
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

        if self._weapon_set == "sword" and self._ready(readiness, "Weapon_4", now):
            return self._decision(
                self._keybinds.offhand_4,
                "Phantasmal Swordsman",
                "Weapon_4",
                timing_delay,
                "sword priority",
            )

        if (
            self._weapon_set == "sword"
            and snapshot.blade_count >= 5
            and self._ready(readiness, "Weapon_5", now)
        ):
            return self._decision(
                self._keybinds.offhand_5,
                "Bladeturn Requiem",
                "Weapon_5",
                timing_delay,
                "five blades",
            )

        if self._weapon_set == "focus" and self._ready(readiness, "Weapon_4", now):
            return self._decision(
                self._keybinds.offhand_4,
                "Phantasmal Warden",
                "Weapon_4",
                timing_delay,
                "focus priority",
            )

        if self._ready(readiness, "Elite", now):
            return self._decision(
                self._keybinds.thousand_cuts,
                "Thousand Cuts",
                "Elite",
                timing_delay,
                "elite off cooldown",
            )

        if self._ready(readiness, "Weapon_3", now):
            return self._decision(
                self._keybinds.weapon_3,
                "Unstable Bladestorm",
                "Weapon_3",
                timing_delay,
                "off cooldown",
            )

        if self._ready(readiness, "Weapon_2", now):
            return self._decision(
                self._keybinds.weapon_2,
                "Bladecall",
                "Weapon_2",
                timing_delay,
                "off cooldown",
            )

        if self._can_use_signet_of_illusions(readiness, now):
            return self._decision(
                self._keybinds.signet_of_illusions or "",
                "Signet of Illusions",
                None,
                timing_delay,
                "Bladesongs unavailable",
            )

        if self._ready(readiness, "WeaponSwap", now):
            return self._decision(
                self._keybinds.weapon_swap,
                "Weapon Swap",
                "WeaponSwap",
                timing_delay,
                "continue weapon loop",
            )

        return self._decision(
            self._keybinds.auto_attack,
            "Auto Attack",
            None,
            timing_delay,
            "no priority skill ready",
        )

    def record_action(self, decision: RotationDecision, now: float) -> None:
        """Advance local loop state only after the input was sent successfully."""

        self._next_action_at = now + decision.delay_seconds
        if decision.slot:
            self._slot_blocked_until[decision.slot] = max(
                self._slot_blocked_until.get(decision.slot, 0.0),
                now + self._SAME_SLOT_GUARD_SECONDS,
            )

        if decision.slot == "Weapon_4":
            if self._weapon_set == "sword":
                self._pending_weapon_swap = True
            elif self._focus_warden_reset_used:
                self._pending_weapon_swap = True
            else:
                self._pending_signet_reset = True
        elif decision.slot == "Heal":
            self._pending_signet_reset = False
            self._focus_warden_reset_used = True
            self._awaiting_warden_reset_until = now + self._WARDEN_RESET_WAIT_SECONDS
        elif decision.slot == "WeaponSwap":
            self._weapon_set = "focus" if self._weapon_set == "sword" else "sword"
            self._pending_weapon_swap = False
            self._pending_signet_reset = False
            self._focus_warden_reset_used = False
            self._awaiting_warden_reset_until = 0.0
            self._ignore_hud_weapon_set_until = now + 0.65
        elif decision.label == "Signet of Illusions":
            self._last_signet_illusions_at = now

    def _can_use_signet_of_illusions(
        self,
        readiness: dict[Optional[str], Optional[bool]],
        now: float,
    ) -> bool:
        return bool(
            self._keybinds.signet_of_illusions
            and now - self._last_signet_illusions_at >= self._SIGNET_ILLUSIONS_GUARD_SECONDS
            and not self._ready(readiness, "Profession_1", now)
            and not self._ready(readiness, "Profession_2", now)
        )

    def _ready(
        self,
        readiness: dict[Optional[str], Optional[bool]],
        slot: str,
        now: float,
    ) -> bool:
        return bool(readiness.get(slot) is True and now >= self._slot_blocked_until.get(slot, 0.0))

    @staticmethod
    def _timing_delay(buff_names: set[str]) -> float:
        if ConditionVirtuosoPlanner._TIMING_DEBUFFS & buff_names:
            return 0.24
        if "quickness" in buff_names:
            return 0.06
        # With no Alacrity, actual HUD readiness determines the next skill;
        # the longer queue interval avoids assuming benchmark recharge timing.
        if "alacrity" not in buff_names:
            return 0.14
        return 0.14

    @staticmethod
    def _decision(
        key: str,
        label: str,
        slot: Optional[str],
        delay_seconds: float,
        reason: str,
    ) -> RotationDecision:
        return RotationDecision(
            key=key,
            label=label,
            slot=slot,
            delay_seconds=delay_seconds,
            reason=reason,
        )


def _configured_key(environment_name: str, default: str) -> str:
    configured = os.getenv(environment_name, "").strip()
    return configured or default


def _configured_optional_key(environment_name: str) -> Optional[str]:
    configured = os.getenv(environment_name, "").strip()
    return configured or None