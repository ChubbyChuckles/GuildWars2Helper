"""Qt-aware controller that orchestrates background automation threads."""

from __future__ import annotations

from threading import Event, Thread
from typing import Callable, Dict, Optional

from PyQt6 import QtCore

from .. import constants
from ..automation import tasks
from ..services.gw2_api import Gw2ApiClient


class TaskController(QtCore.QObject):
    status_changed = QtCore.pyqtSignal(str)
    farming_started = QtCore.pyqtSignal()
    farming_completed = QtCore.pyqtSignal(dict)
    pause_state_changed = QtCore.pyqtSignal(bool)
    character_progress = QtCore.pyqtSignal(dict)
    bank_summary_loaded = QtCore.pyqtSignal(object)
    bank_summary_failed = QtCore.pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._farm_thread: Optional[Thread] = None
        self._pause_event = Event()
        self._pause_event.set()
        self._is_paused = False
        self._should_skip_character: Optional[Callable[[str], bool]] = None
        self._bank_load_thread: Optional[Thread] = None

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

    def run_alt_char_farm(
        self,
        *,
        should_skip_character: Optional[Callable[[str], bool]] = None,
    ) -> None:
        if self.is_farming_active():
            self.status_changed.emit("Farming already running.")
            return

        self._pause_event.set()
        self._is_paused = False
        self._should_skip_character = should_skip_character

        def worker() -> None:
            try:
                tasks.alt_char_farm(
                    self.status_changed.emit,
                    self._pause_event,
                    self._handle_farm_completion,
                    self._should_skip_character,
                    self._handle_character_progress,
                )
            except Exception as exc:  # pragma: no cover - runtime safeguard
                self.status_changed.emit(f"Farming failed: {exc}")
                self._handle_farm_completion({"error": str(exc)})
            finally:
                self._pause_event.set()
                self._is_paused = False
                self.pause_state_changed.emit(False)
                self._farm_thread = None
                self._should_skip_character = None

        self._farm_thread = Thread(target=worker, daemon=True)
        self._farm_thread.start()
        self.farming_started.emit()
        self.status_changed.emit("Farming started.")

    def lookup_character(self, name: str) -> None:
        Thread(target=tasks.look_for_char, args=(name,), daemon=True).start()

    def copy_next_event_code(self) -> Optional[str]:
        return tasks.clipboard_event_code()

    def load_bank_summary(self) -> bool:
        """Load account-bank metrics without blocking the Qt event loop."""

        if self._bank_load_thread is not None and self._bank_load_thread.is_alive():
            return False

        def worker() -> None:
            try:
                summary = Gw2ApiClient().get_bank_summary()
            except Exception as exc:  # pragma: no cover - network/runtime safeguard
                self.bank_summary_failed.emit(str(exc))
            else:
                self.bank_summary_loaded.emit(summary)
            finally:
                self._bank_load_thread = None

        self._bank_load_thread = Thread(target=worker, daemon=True)
        self._bank_load_thread.start()
        return True

    def pause_farming(self) -> None:
        if not self.is_farming_active():
            self.status_changed.emit("No active farming routine to pause.")
            return
        if self._is_paused:
            return
        self._pause_event.clear()
        self._is_paused = True
        self.pause_state_changed.emit(True)
        self.status_changed.emit("Farming paused.")

    def resume_farming(self) -> None:
        if not self.is_farming_active():
            self.status_changed.emit("No active farming routine to resume.")
            return
        if not self._is_paused:
            return
        self._pause_event.set()
        self._is_paused = False
        self.pause_state_changed.emit(False)
        self.status_changed.emit("Farming resumed.")

    def toggle_pause(self) -> None:
        if self._is_paused:
            self.resume_farming()
        else:
            self.pause_farming()

    def is_farming_active(self) -> bool:
        return self._farm_thread is not None and self._farm_thread.is_alive()

    def is_paused(self) -> bool:
        return self._is_paused

    def _handle_farm_completion(self, payload: Optional[Dict[str, object]]) -> None:
        data = payload or {}
        self.farming_completed.emit(data)

    def _handle_character_progress(self, payload: Dict[str, object]) -> None:
        self.character_progress.emit(payload)
