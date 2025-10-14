"""Qt-aware controller that orchestrates background automation threads."""

from __future__ import annotations

from threading import Thread
from typing import Optional

from PyQt6 import QtCore

from .. import constants
from ..automation import tasks


class TaskController(QtCore.QObject):
    status_changed = QtCore.pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()

    def set_empty_chars_enabled(self, enabled: bool) -> None:
        if constants.EMPTY_CHARS == enabled:
            return
        constants.set_empty_chars_enabled(enabled)
        state = "enabled" if enabled else "disabled"
        self.status_changed.emit(f"Empty character routine {state}.")

    def set_shutdown_enabled(self, enabled: bool) -> None:
        if constants.SHUTDOWN == enabled:
            return
        constants.set_shutdown_enabled(enabled)
        state = "enabled" if enabled else "disabled"
        self.status_changed.emit(f"Shutdown after farming {state}.")

    def run_skyscale_bug(self) -> None:
        Thread(target=tasks.do_skyscale_bug, daemon=True).start()

    def run_alt_char_farm(self) -> None:
        Thread(
            target=tasks.alt_char_farm,
            args=(self.status_changed.emit,),
            daemon=True,
        ).start()

    def lookup_character(self, name: str) -> None:
        Thread(target=tasks.look_for_char, args=(name,), daemon=True).start()

    def copy_next_event_code(self) -> Optional[str]:
        return tasks.clipboard_event_code()
