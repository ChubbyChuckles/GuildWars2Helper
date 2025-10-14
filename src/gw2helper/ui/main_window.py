"""PyQt6 user interface for the Guild Wars 2 helper automation."""

from __future__ import annotations

import time
from threading import Thread
from typing import List, Optional

from PyQt6 import QtCore, QtWidgets

from ..automation import tasks
from ..controllers.task_controller import TaskController


class ScrollingLabel(QtWidgets.QLabel):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._raw_text = ""  # Text before padding
        self._display_text = ""
        self._scroll_enabled = False
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(100)
        self._stop_time: Optional[float] = None
        self.setMinimumWidth(240)

    def set_message(
        self, text: str, scroll: bool = False, duration: float = 10.0
    ) -> None:
        padded = f"    {text}    "
        self._raw_text = padded
        self._display_text = padded
        self._scroll_enabled = scroll
        self._stop_time = time.monotonic() + duration if scroll else None
        super().setText(self._display_text)

    def _tick(self) -> None:
        if not self._scroll_enabled:
            return
        if self._stop_time is not None and time.monotonic() > self._stop_time:
            self._scroll_enabled = False
            self._display_text = self._raw_text
            super().setText(self._display_text)
            return
        if self._display_text:
            self._display_text = self._display_text[1:] + self._display_text[0]
            super().setText(self._display_text)


class MainWindow(QtWidgets.QWidget):
    characters_loaded = QtCore.pyqtSignal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Guild Wars 2 Helper")
        self.controller = TaskController()
        self._build_ui()
        self._connect_signals()
        self._load_characters_async()
        self._start_event_timer()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.banner_label = ScrollingLabel()
        self.banner_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.banner_label.set_message("Control Panel", scroll=False)
        layout.addWidget(self.banner_label)

        self.character_combo = QtWidgets.QComboBox()
        self.character_combo.addItem("Loading characters...")
        layout.addWidget(self.character_combo)

        button_row = QtWidgets.QHBoxLayout()
        layout.addLayout(button_row)

        self.farm_button = QtWidgets.QPushButton("Farm")
        button_row.addWidget(self.farm_button)

        self.bug_button = QtWidgets.QPushButton("Bug")
        button_row.addWidget(self.bug_button)

        self.cc_checkbox = QtWidgets.QCheckBox("CC")
        button_row.addWidget(self.cc_checkbox)

        self.start_button = QtWidgets.QPushButton("Start")
        button_row.addWidget(self.start_button)

        self.wvw_button = QtWidgets.QPushButton("WvW")
        button_row.addWidget(self.wvw_button)

        self.status_label = QtWidgets.QLabel("Ready")
        layout.addWidget(self.status_label)

    def _connect_signals(self) -> None:
        self.farm_button.clicked.connect(self.controller.run_alt_char_farm)
        self.bug_button.clicked.connect(self.controller.run_skyscale_bug)
        self.wvw_button.clicked.connect(self.controller.run_wvw)
        self.start_button.clicked.connect(self.controller.toggle_rotation)
        self.cc_checkbox.stateChanged.connect(
            lambda state: self.controller.set_cc_enabled(
                state == QtCore.Qt.CheckState.Checked
            )
        )
        self.character_combo.currentTextChanged.connect(self._on_character_selected)

        self.controller.status_changed.connect(self.status_label.setText)
        self.controller.rotation_state_changed.connect(self._update_rotation_button)

        self.characters_loaded.connect(self._populate_characters)

    def _load_characters_async(self) -> None:
        def worker() -> None:
            characters: List[str]
            try:
                characters = tasks.get_character_list()
            except Exception:
                characters = []
            self.characters_loaded.emit(characters)

        Thread(target=worker, daemon=True).start()

    def _populate_characters(self, characters: List[str]) -> None:
        self.character_combo.clear()
        if not characters:
            self.character_combo.addItem("No characters found")
        else:
            self.character_combo.addItem("Select a Character")
            for name in characters:
                self.character_combo.addItem(name)

    def _on_character_selected(self, name: str) -> None:
        if not name or name in {
            "Loading characters...",
            "Select a Character",
            "No characters found",
        }:
            return
        self.status_label.setText(f"Character {name} selected")
        self.banner_label.set_message(f"Character {name} selected", scroll=True)
        self.controller.lookup_character(name)

    def _update_rotation_button(self, running: bool) -> None:
        self.start_button.setText("Stop" if running else "Start")
        if running:
            self.status_label.setText("Rotation running...")
        else:
            self.status_label.setText("Rotation stopped")

    def _start_event_timer(self) -> None:
        self._event_timer = QtCore.QTimer(self)
        self._event_timer.timeout.connect(self._refresh_event_banner)
        self._event_timer.start(60000)
        self._refresh_event_banner()

    def _refresh_event_banner(self) -> None:
        event_text = self.controller.copy_next_event_code()
        if event_text:
            self.banner_label.set_message(event_text, scroll=True)
        else:
            self.banner_label.set_message("Control Panel", scroll=False)


def create_window() -> MainWindow:
    return MainWindow()
