"""Qt-aware controller that orchestrates background automation threads."""

from __future__ import annotations

from threading import Event, Thread
from typing import Callable, Dict, Optional

from PyQt6 import QtCore

from .. import constants
from ..automation import tasks
from ..services.arcdps_telemetry import ArcDpsCombatMonitor, CombatTelemetrySnapshot
from ..services.gw2_api import Gw2ApiClient


class TaskController(QtCore.QObject):
    status_changed = QtCore.pyqtSignal(str)
    farming_started = QtCore.pyqtSignal()
    farming_completed = QtCore.pyqtSignal(dict)
    pause_state_changed = QtCore.pyqtSignal(bool)
    character_progress = QtCore.pyqtSignal(dict)
    bank_summary_loaded = QtCore.pyqtSignal(object)
    bank_summary_failed = QtCore.pyqtSignal(str)
    rotation_state_changed = QtCore.pyqtSignal(bool)

    def __init__(self, combat_monitor: Optional[ArcDpsCombatMonitor] = None) -> None:
        super().__init__()
        self._farm_thread: Optional[Thread] = None
        self._pause_event = Event()
        self._pause_event.set()
        self._is_paused = False
        self._should_skip_character: Optional[Callable[[str], bool]] = None
        self._bank_load_thread: Optional[Thread] = None
        self._rotation_thread: Optional[Thread] = None
        self._rotation_stop_event: Optional[Event] = None
        self._combat_monitor = combat_monitor or ArcDpsCombatMonitor(
            hud_supplier=tasks.read_combat_hud_status
        )

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

    def set_combat_cc_enabled(self, enabled: bool) -> None:
        if constants.COMBAT_CC_ENABLED == enabled:
            return
        constants.set_combat_cc_enabled(enabled)
        state = "enabled" if enabled else "disabled"
        self.status_changed.emit(f"Combat crowd control {state}.")

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
        if self.is_rotation_active():
            self.status_changed.emit("Stop the damage rotation before starting farming.")
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

    def start_combat_monitor(self) -> None:
        self._combat_monitor.start()

    def stop_combat_monitor(self) -> None:
        self._combat_monitor.stop()

    def combat_telemetry_snapshot(self) -> CombatTelemetrySnapshot:
        return self._combat_monitor.snapshot()

    def start_rotation(self) -> bool:
        """Start the adaptive condition Virtuoso rotation in a daemon thread."""

        if self.is_farming_active():
            self.status_changed.emit("Pause or finish farming before starting the damage rotation.")
            return False
        if self.is_rotation_active():
            return False

        stop_event = Event()
        self._rotation_stop_event = stop_event

        def worker() -> None:
            try:
                tasks.do_condition_virtuoso_rotation(
                    stop_event,
                    self.combat_telemetry_snapshot,
                    constants.is_combat_cc_enabled,
                    self.status_changed.emit,
                )
            except Exception as exc:  # pragma: no cover - runtime safeguard
                self.status_changed.emit(f"Damage rotation failed: {exc}")
            finally:
                self._rotation_stop_event = None
                self._rotation_thread = None
                self.rotation_state_changed.emit(False)

        self._rotation_thread = Thread(target=worker, daemon=True)
        self._rotation_thread.start()
        self.rotation_state_changed.emit(True)
        self.status_changed.emit("Condition Virtuoso rotation started.")
        return True

    def stop_rotation(self) -> bool:
        """Request a running damage rotation to stop at its next skill scan."""

        if not self.is_rotation_active() or self._rotation_stop_event is None:
            return False
        self._rotation_stop_event.set()
        self.status_changed.emit("Stopping damage rotation.")
        return True

    def toggle_rotation(self) -> bool:
        if self.is_rotation_active():
            return self.stop_rotation()
        return self.start_rotation()

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

    def is_rotation_active(self) -> bool:
        return self._rotation_thread is not None and self._rotation_thread.is_alive()

    def is_paused(self) -> bool:
        return self._is_paused

    def _handle_farm_completion(self, payload: Optional[Dict[str, object]]) -> None:
        data = payload or {}
        self.farming_completed.emit(data)

    def _handle_character_progress(self, payload: Dict[str, object]) -> None:
        self.character_progress.emit(payload)
