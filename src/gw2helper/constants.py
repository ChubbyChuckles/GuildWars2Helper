"""Shared configuration constants for the Guild Wars 2 helper application."""

from __future__ import annotations

CHARS_TO_SKIP = ["Brooke Kensington", "Haylene Blackfyre"]

# Flags controlling automation behaviour (mutable via setter helpers).
EMPTY_CHARS = False
SHUTDOWN = True
COMBAT_CC_ENABLED = False


def set_empty_chars_enabled(value: bool) -> None:
    """Enable or disable the character emptying routine."""

    global EMPTY_CHARS
    EMPTY_CHARS = bool(value)


def set_shutdown_enabled(value: bool) -> None:
    """Enable or disable automatic system shutdown when farming completes."""

    global SHUTDOWN
    SHUTDOWN = bool(value)


def set_combat_cc_enabled(value: bool) -> None:
    """Enable conditional crowd-control skills during the combat rotation."""

    global COMBAT_CC_ENABLED
    COMBAT_CC_ENABLED = bool(value)


def is_empty_chars_enabled() -> bool:
    return EMPTY_CHARS


def is_shutdown_enabled() -> bool:
    return SHUTDOWN


def is_combat_cc_enabled() -> bool:
    return COMBAT_CC_ENABLED
