"""Shared configuration constants for the Guild Wars 2 helper application."""

from __future__ import annotations

CHARS_TO_SKIP = ["Brooke Kensington", "Haylene Blackfyre"]

# Flags controlling automation behaviour (mutable via setter helpers).
EMPTY_CHARS = False
SHUTDOWN = True


def set_empty_chars_enabled(value: bool) -> None:
    """Enable or disable the character emptying routine."""

    global EMPTY_CHARS
    EMPTY_CHARS = bool(value)


def set_shutdown_enabled(value: bool) -> None:
    """Enable or disable automatic system shutdown when farming completes."""

    global SHUTDOWN
    SHUTDOWN = bool(value)


def is_empty_chars_enabled() -> bool:
    return EMPTY_CHARS


def is_shutdown_enabled() -> bool:
    return SHUTDOWN
