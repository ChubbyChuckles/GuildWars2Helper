"""Persistence helpers for Guild Wars 2 helper application state."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

_STATE_DIR = Path.home() / ".guildwars2helper"
_STATE_FILE = _STATE_DIR / "state.json"
EMPTY_AFTER_FARM_DAYS = 7


@dataclass
class AppState:
    window_x: Optional[int] = None
    window_y: Optional[int] = None
    window_width: int = 520
    window_height: int = 460
    last_empty_timestamp: Optional[str] = None
    last_farm_date: Optional[str] = None
    farm_count_since_empty: int = 0
    characters_farmed_last_run: int = 0
    farmed_characters: Dict[str, Dict[str, Optional[str]]] = field(default_factory=dict)
    last_total_characters: int = 0
    last_remaining_characters: int = 0
    farming_days_since_empty: list[str] = field(default_factory=list)
    character_farm_counts: Dict[str, int] = field(default_factory=dict)
    character_farm_counts_since_empty: Dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppState":
        window = data.get("window", {})
        stats = data.get("stats", {})
        emptying = data.get("emptying", {})
        if not isinstance(emptying, dict):
            emptying = {}
        raw_characters = stats.get("farmed_characters", {})
        farmed_characters: Dict[str, Dict[str, Optional[str]]] = {}
        if isinstance(raw_characters, dict):
            for key, value in raw_characters.items():
                name = str(key)
                if isinstance(value, dict):
                    reset_key = _coerce_str(value.get("reset_key"))
                    timestamp = _coerce_str(value.get("timestamp"))
                else:
                    reset_key = _coerce_str(value)
                    timestamp = None
                if reset_key:
                    farmed_characters[name] = {
                        "reset_key": reset_key,
                        "timestamp": timestamp,
                    }

        return cls(
            window_x=_coerce_int(window.get("x")),
            window_y=_coerce_int(window.get("y")),
            window_width=_coerce_int(window.get("width")) or 520,
            window_height=_coerce_int(window.get("height")) or 460,
            last_empty_timestamp=_coerce_str(stats.get("last_empty_timestamp")),
            last_farm_date=_coerce_str(stats.get("last_farm_date")),
            farm_count_since_empty=_coerce_int(stats.get("farm_count_since_empty"))
            or 0,
            characters_farmed_last_run=_coerce_int(
                stats.get("characters_farmed_last_run")
            )
            or 0,
            farmed_characters=farmed_characters,
            last_total_characters=_coerce_int(stats.get("last_total_characters")) or 0,
            last_remaining_characters=_coerce_int(
                stats.get("last_remaining_characters")
            )
            or 0,
            farming_days_since_empty=_coerce_string_list(
                emptying.get("farming_days_since_empty")
            ),
            character_farm_counts=_coerce_count_map(
                emptying.get("character_farm_counts")
            ),
            character_farm_counts_since_empty=_coerce_count_map(
                emptying.get("character_farm_counts_since_empty")
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return {
            "window": {
                "x": data["window_x"],
                "y": data["window_y"],
                "width": data["window_width"],
                "height": data["window_height"],
            },
            "stats": {
                "last_empty_timestamp": data["last_empty_timestamp"],
                "last_farm_date": data["last_farm_date"],
                "farm_count_since_empty": data["farm_count_since_empty"],
                "characters_farmed_last_run": data["characters_farmed_last_run"],
                "farmed_characters": data["farmed_characters"],
                "last_total_characters": data["last_total_characters"],
                "last_remaining_characters": data["last_remaining_characters"],
            },
            "emptying": {
                "farming_days_since_empty": data["farming_days_since_empty"],
                "character_farm_counts": data["character_farm_counts"],
                "character_farm_counts_since_empty": data[
                    "character_farm_counts_since_empty"
                ],
            },
        }


def load_app_state() -> AppState:
    if not _STATE_FILE.exists():
        return AppState()
    try:
        raw = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return AppState()
    return AppState.from_dict(raw)


def save_app_state(state: AppState) -> None:
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(state.to_dict(), ensure_ascii=True, indent=2)
    _STATE_FILE.write_text(serialized, encoding="utf-8")


def record_farming_day(state: AppState, farming_day: str) -> bool:
    """Record one distinct farming day for the current emptying cycle."""

    normalized_day = farming_day.strip()
    if not normalized_day or normalized_day in state.farming_days_since_empty:
        return False
    state.farming_days_since_empty.append(normalized_day)
    return True


def record_character_farmed(
    state: AppState,
    name: str,
    *,
    count_toward_current_cycle: bool = True,
) -> None:
    """Track character farming frequency across all time and this cycle."""

    normalized_name = name.strip()
    if not normalized_name:
        return
    state.character_farm_counts[normalized_name] = (
        state.character_farm_counts.get(normalized_name, 0) + 1
    )
    if count_toward_current_cycle:
        state.character_farm_counts_since_empty[normalized_name] = (
            state.character_farm_counts_since_empty.get(normalized_name, 0) + 1
        )


def complete_emptying_cycle(state: AppState, timestamp: str) -> None:
    """Reset only the schedule data that belongs to the completed cycle."""

    state.last_empty_timestamp = timestamp
    state.farm_count_since_empty = 0
    state.farming_days_since_empty.clear()
    state.character_farm_counts_since_empty.clear()


def farming_days_since_empty_count(state: AppState) -> int:
    """Return the number of distinct farming days in the active cycle."""

    return len(set(state.farming_days_since_empty))


def is_emptying_due(
    state: AppState,
    required_farming_days: int = EMPTY_AFTER_FARM_DAYS,
) -> bool:
    """Return whether the current cycle has reached its emptying cadence."""

    if required_farming_days <= 0:
        raise ValueError("required_farming_days must be greater than zero")
    return farming_days_since_empty_count(state) >= required_farming_days


def _coerce_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_str(value: Any) -> Optional[str]:
    if isinstance(value, str) and value:
        return value
    return None


def _coerce_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    values: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        normalized = item.strip()
        if normalized and normalized not in values:
            values.append(normalized)
    return values


def _coerce_count_map(value: Any) -> Dict[str, int]:
    if not isinstance(value, dict):
        return {}
    counts: Dict[str, int] = {}
    for raw_name, raw_count in value.items():
        name = str(raw_name).strip()
        count = _coerce_int(raw_count)
        if name and count is not None and count > 0:
            counts[name] = count
    return counts
