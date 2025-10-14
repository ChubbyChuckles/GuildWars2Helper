"""Notification utilities for the Guild Wars 2 helper."""

from __future__ import annotations

import requests
import winsound


def play_beep(frequency: int = 1000, duration: int = 500) -> None:
    """Play a simple beep to alert the player."""
    winsound.Beep(frequency, duration)


def send_message(message: str) -> None:
    """Send a message using the configured Telegram bot."""
    token = "6201024684:AAE1NsieSJdFu-sPKaYN7bzLSqE_064mYWw"
    chat_id = "775995383"
    payload = {
        "chat_id": chat_id,
        "text": str(message),
    }
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, data=payload, timeout=5)
    except requests.RequestException:
        # Failing to notify should not crash the automation.
        pass
