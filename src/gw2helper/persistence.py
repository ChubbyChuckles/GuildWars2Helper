"""Persistence helpers for Guild Wars 2 helper application state."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, Optional

_STATE_DIR = Path.home() / ".guildwars2helper"
_STATE_FILE = _STATE_DIR / "state.json"


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
    farmed_characters: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppState":
        window = data.get("window", {})
        stats = data.get("stats", {})
        raw_characters = stats.get("farmed_characters", {})
        farmed_characters: Dict[str, str] = {}
        if isinstance(raw_characters, dict):
            for key, value in raw_characters.items():
                name = str(key)
                value_str = _coerce_str(value)
                if value_str:
                    farmed_characters[name] = value_str

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


def _coerce_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_str(value: Any) -> Optional[str]:
    if isinstance(value, str) and value:
        return value
    return None
