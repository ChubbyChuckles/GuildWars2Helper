"""Qt-aware controller that orchestrates background automation threads."""

from __future__ import annotations

import threading
from threading import Event, Thread
from typing import Optional

import keyboard
from PyQt6 import QtCore

from ..automation import tasks


class TaskController(QtCore.QObject):
    status_changed = QtCore.pyqtSignal(str)
    rotation_state_changed = QtCore.pyqtSignal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._rotation_stop_event: Event = Event()
        self._rotation_thread: Optional[Thread] = None
        self._cc_enabled = False
        self._register_hotkeys()

    def _register_hotkeys(self) -> None:
        modifiers = [
            "pause",
            "w+pause",
            "s+pause",
            "a+pause",
            "d+pause",
            "w+d+pause",
            "s+d+pause",
            "w+a+pause",
            "s+a+pause",
        ]
        for combo in modifiers:
            keyboard.add_hotkey(combo, self.toggle_rotation)

    def set_cc_enabled(self, enabled: bool) -> None:
        self._cc_enabled = enabled

    def _get_cc_state(self) -> bool:
        return self._cc_enabled

    def toggle_rotation(self) -> None:
        if self._rotation_thread and self._rotation_thread.is_alive():
            self.stop_rotation()
        else:
            self.start_rotation()

    def start_rotation(self) -> None:
        if self._rotation_thread and self._rotation_thread.is_alive():
            return
        self._rotation_stop_event.clear()
        thread = Thread(
            target=tasks.do_rotation,
            args=(self._rotation_stop_event, self._get_cc_state),
            daemon=True,
        )
        thread.start()
        self._rotation_thread = thread
        self.rotation_state_changed.emit(True)

    def stop_rotation(self) -> None:
        if not self._rotation_thread:
            return
        self._rotation_stop_event.set()
        self._rotation_thread = None
        self.rotation_state_changed.emit(False)

    def run_skyscale_bug(self) -> None:
        Thread(target=tasks.do_skyscale_bug, daemon=True).start()

    def run_alt_char_farm(self) -> None:
        Thread(
            target=tasks.alt_char_farm, args=(self.status_changed.emit,), daemon=True
        ).start()

    def run_wvw(self) -> None:
        Thread(target=tasks.farm_wvw, daemon=True).start()

    def lookup_character(self, name: str) -> None:
        Thread(target=tasks.look_for_char, args=(name,), daemon=True).start()

    def copy_next_event_code(self) -> Optional[str]:
        return tasks.clipboard_event_code()
