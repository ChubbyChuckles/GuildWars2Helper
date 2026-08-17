"""Detect the Guild Wars 2 character-select screen through MumbleLink."""

from __future__ import annotations

import time
from typing import Optional

import psutil

from .mumble import MumbleLink

def is_in_char_select_screen(
    timeout: float = 0.5,
    poll_interval: float = 0.05,
) -> Optional[bool]:
    """Return whether a running Guild Wars 2 client is at character select.

    MumbleLink's ``uiTick`` advances while a character is in the game world and
    remains unchanged at character select. ``None`` means the game state could
    not be determined.
    """

    if timeout <= 0:
        raise ValueError("timeout must be greater than zero")
    if poll_interval <= 0:
        raise ValueError("poll_interval must be greater than zero")

    try:
        mumble_link = MumbleLink()
    except OSError:
        return None

    try:
        link, context = mumble_link.read()
        if not _is_gw2_process(context.processId) or not link.uiTick:
            return None

        initial_tick = link.uiTick
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return True
            time.sleep(min(poll_interval, remaining))
            link, _ = mumble_link.read()
            if link.uiTick != initial_tick:
                return False
    except OSError:
        return None
    finally:
        mumble_link.close()


def _is_gw2_process(process_id: int) -> bool:
    try:
        return psutil.Process(process_id).name().lower() == "gw2-64.exe"
    except (psutil.Error, ValueError):
        return False
