"""PyQt6 user interface for the Guild Wars 2 helper automation."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys
import time
from datetime import date, datetime, timedelta, timezone
from threading import Thread
from typing import Dict, List, Optional

from PyQt6 import QtCore, QtGui, QtWidgets

from .. import constants, persistence
from ..automation import tasks
from ..controllers.task_controller import TaskController

if sys.platform == "win32":

    class _F5Hotkey(QtCore.QObject, QtCore.QAbstractNativeEventFilter):
        triggered = QtCore.pyqtSignal()

        _WM_HOTKEY = 0x0312
        _MOD_NOREPEAT = 0x4000
        _VK_F5 = 0x74

        def __init__(self, window: QtWidgets.QWidget) -> None:
            super().__init__(window)
            self._window = window
            self._id = 1
            self._user32 = ctypes.windll.user32
            self._installed = False
            self._registered = False
            self._hwnd: Optional[int] = None

        def register(self) -> bool:
            if self._registered:
                return True
            hwnd = int(self._window.winId())
            if not hwnd:
                return False
            if not self._user32.RegisterHotKey(
                hwnd,
                self._id,
                self._MOD_NOREPEAT,
                self._VK_F5,
            ):
                return False
            app = QtWidgets.QApplication.instance()
            if app is None:
                self._user32.UnregisterHotKey(hwnd, self._id)
                return False
            app.installNativeEventFilter(self)
            self._installed = True
            self._registered = True
            self._hwnd = hwnd
            return True

        def nativeEventFilter(self, event_type: str, message: int) -> tuple[bool, int]:
            if not self._registered:
                return False, 0
            if event_type not in {"windows_generic_MSG", "windows_dispatcher_MSG"}:
                return False, 0
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == self._WM_HOTKEY and msg.wParam == self._id:
                self.triggered.emit()
                return True, 0
            return False, 0

        def dispose(self) -> None:
            if self._installed:
                app = QtWidgets.QApplication.instance()
                if app is not None:
                    app.removeNativeEventFilter(self)
                self._installed = False
            if self._registered and self._hwnd is not None:
                self._user32.UnregisterHotKey(self._hwnd, self._id)
                self._registered = False
                self._hwnd = None

        @property
        def is_registered(self) -> bool:
            return self._registered

else:
    _F5Hotkey = None  # type: ignore[assignment]


class TitleBar(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._drag_start: Optional[QtCore.QPoint] = None
        self._frame_start: Optional[QtCore.QPoint] = None
        self.setObjectName("CustomTitleBar")
        self.setFixedHeight(48)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(12)

        self.title_label = QtWidgets.QLabel("Guild Wars 2 Helper")
        self.title_label.setObjectName("TitleBarLabel")
        self.title_label.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        layout.addWidget(self.title_label)

        layout.addStretch()

        self.min_button = QtWidgets.QToolButton()
        self.min_button.setObjectName("TitleBarButton")
        self.min_button.setText("–")
        self.min_button.setCursor(
            QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        )
        self.min_button.setToolTip("Minimize")
        self.min_button.clicked.connect(self._on_minimize)
        layout.addWidget(self.min_button)

        self.close_button = QtWidgets.QToolButton()
        self.close_button.setObjectName("TitleBarButton")
        self.close_button.setText("✕")
        self.close_button.setCursor(
            QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        )
        self.close_button.setToolTip("Close")
        self.close_button.clicked.connect(self._on_close)
        layout.addWidget(self.close_button)

    def _on_minimize(self) -> None:
        self.window().showMinimized()

    def _on_close(self) -> None:
        self.window().close()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()
            self._frame_start = self.window().frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        if (
            self._drag_start is not None
            and self._frame_start is not None
            and event.buttons() & QtCore.Qt.MouseButton.LeftButton
        ):
            delta = event.globalPosition().toPoint() - self._drag_start
            self.window().move(self._frame_start + delta)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_start = None
            self._frame_start = None
            event.accept()
            return
        super().mouseReleaseEvent(event)


class StatusBar(QtWidgets.QFrame):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatusBar")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.setFixedHeight(46)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)

        self._icon = QtWidgets.QLabel("⏱")
        self._icon.setObjectName("StatusIcon")
        self._icon.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._icon)

        self.label = QtWidgets.QLabel("Uptime 00:00:00")
        self.label.setObjectName("StatusBarLabel")
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.label)

        layout.addStretch()

    def set_uptime(self, uptime_text: str) -> None:
        self.label.setText(uptime_text)


class ScrollingLabel(QtWidgets.QLabel):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._raw_text = ""
        self._display_text = ""
        self._scroll_enabled = False
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(100)
        self._stop_time: Optional[float] = None
        self.setMinimumWidth(260)

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
        self.setObjectName("MainWindow")
        self._app_state = persistence.load_app_state()
        if not isinstance(self._app_state.farmed_characters, dict):
            self._app_state.farmed_characters = {}
        self._reset_tz = timezone(timedelta(hours=2))
        self._prune_stale_farmed_characters()
        self._app_start_time = time.monotonic()
        self.controller = TaskController()
        self._save_state_timer = QtCore.QTimer(self)
        self._save_state_timer.setSingleShot(True)
        self._save_state_timer.timeout.connect(self._persist_state)
        self._total_characters = max(0, self._app_state.last_total_characters)
        self._remaining_characters = max(0, self._app_state.last_remaining_characters)
        self._remaining_characters = min(
            self._remaining_characters,
            max(0, self._total_characters - self._characters_farmed_today_count()),
        )
        self._app_state.last_remaining_characters = self._remaining_characters
        self._setup_window()
        self._build_ui()
        self._connect_signals()
        self._load_characters_async()
        self._start_event_timer()
        self._start_uptime_timer()
        self._refresh_stats_display()
        self._pause_shortcut = QtGui.QShortcut(QtGui.QKeySequence("F5"), self)
        self._pause_shortcut.setContext(QtCore.Qt.ShortcutContext.ApplicationShortcut)
        self._pause_shortcut.activated.connect(self._toggle_pause)
        self._global_hotkey = self._create_global_hotkey()

    def _setup_window(self) -> None:
        flags = (
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.Window
            | QtCore.Qt.WindowType.WindowSystemMenuHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowFlags(flags)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        width = self._app_state.window_width or 520
        height = self._app_state.window_height or 460
        self.resize(width, height)
        if (
            self._app_state.window_x is not None
            and self._app_state.window_y is not None
        ):
            self.move(self._app_state.window_x, self._app_state.window_y)
        self.setFont(QtGui.QFont("Segoe UI", 9))
        self._apply_styles()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
#MainWindow {
    background-color: transparent;
}
#CustomTitleBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #3f4c92, stop:0.5 #2b325d, stop:1 #1b203b);
    color: #f6f8ff;
    border-top-left-radius: 18px;
    border-top-right-radius: 18px;
}
#TitleBarLabel {
    font-size: 18px;
    font-weight: 600;
    letter-spacing: 0.8px;
}
#TitleBarButton {
    background-color: transparent;
    color: #e3e7ff;
    border: none;
    font-size: 17px;
    padding: 0 10px;
}
#TitleBarButton:hover {
    background-color: rgba(255, 255, 255, 0.12);
    border-radius: 10px;
}
#TitleBarButton:pressed {
    background-color: rgba(255, 255, 255, 0.22);
}
#MainContainer {
    background: qradialgradient(cx:0.3, cy:0.3, radius:1.0,
                                stop:0 rgba(88, 104, 205, 0.35),
                                stop:1 rgba(22, 26, 46, 0.92));
    border-bottom-left-radius: 18px;
    border-bottom-right-radius: 18px;
    border: 1px solid rgba(92, 112, 190, 0.35);
    border-top: none;
}
QFrame#MainPanel {
    background: rgba(23, 28, 51, 0.85);
    border-radius: 16px;
    border: 1px solid rgba(110, 135, 210, 0.25);
}
#BannerLabel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                 stop:0 rgba(94, 127, 255, 0.35),
                                 stop:1 rgba(136, 88, 255, 0.30));
    border-radius: 12px;
    border: 1px solid rgba(133, 167, 255, 0.35);
    padding: 12px 18px;
    font-weight: 700;
    font-size: 16px;
    color: #f4f6ff;
}
QLabel {
    color: #ecf0ff;
}
#StatusMessage {
    color: #d5dbff;
    font-size: 13px;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #5162f0, stop:1 #2e3bbd);
    color: #ffffff;
    border: 1px solid rgba(124, 149, 255, 0.35);
    border-radius: 10px;
    padding: 10px 22px;
    font-weight: 600;
    letter-spacing: 0.4px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #6e7ef7, stop:1 #3d4dd0);
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #2c3bc0, stop:1 #1f2a8a);
}
QComboBox {
    background: rgba(28, 33, 58, 0.9);
    color: #f3f5ff;
    border-radius: 10px;
    border: 1px solid rgba(104, 126, 211, 0.45);
    padding: 8px 14px;
    font-weight: 600;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background: rgba(22, 26, 46, 0.95);
    color: #f3f5ff;
    border-radius: 8px;
    selection-background-color: rgba(102, 123, 210, 0.6);
    selection-color: #ffffff;
}
QCheckBox {
    color: #d7ddff;
    font-weight: 500;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 6px;
    border: 2px solid rgba(127, 159, 255, 0.6);
    background: rgba(33, 40, 66, 0.9);
}
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #6d82ff, stop:1 #9b6dff);
    border-color: rgba(148, 175, 255, 0.9);
}
#StatPill {
    background: rgba(33, 40, 66, 0.9);
    border-radius: 12px;
    border: 1px solid rgba(120, 140, 210, 0.4);
    padding: 8px 14px;
    font-weight: 600;
    letter-spacing: 0.4px;
    color: #dde3ff;
}
#StatPill[state="positive"] {
    border-color: rgba(108, 200, 170, 0.7);
    color: #9de8c7;
}
#StatPill[state="negative"] {
    border-color: rgba(255, 140, 150, 0.7);
    color: #ff9fb1;
}
#StatPill[state="info"] {
    border-color: rgba(144, 162, 230, 0.7);
    color: #c8d5ff;
}
#StatPill[state="neutral"] {
    border-color: rgba(120, 140, 210, 0.4);
    color: #dde3ff;
}
#StatusBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 rgba(36, 44, 80, 0.95),
                                stop:1 rgba(22, 26, 48, 0.95));
    border-radius: 14px;
    border: 1px solid rgba(100, 120, 190, 0.35);
    color: #dde3ff;
}
#StatusBarLabel {
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.4px;
}
#StatusIcon {
    color: #8aa3ff;
    font-size: 16px;
}
QToolTip {
    background-color: rgba(30, 34, 60, 0.95);
    color: #f1f3ff;
    border: 1px solid rgba(120, 140, 210, 0.6);
    padding: 6px 10px;
    border-radius: 8px;
    font-size: 11px;
}
"""
        )

    def _build_ui(self) -> None:
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.title_bar = TitleBar(self)
        outer_layout.addWidget(self.title_bar)

        self._content_frame = QtWidgets.QFrame()
        self._content_frame.setObjectName("MainContainer")
        outer_layout.addWidget(self._content_frame)

        self._apply_soft_shadow(
            self._content_frame,
            QtGui.QColor(10, 10, 30, 200),
            blur=36,
            y_offset=18,
        )

        content_layout = QtWidgets.QVBoxLayout(self._content_frame)
        content_layout.setContentsMargins(28, 28, 28, 22)
        content_layout.setSpacing(22)

        main_panel = QtWidgets.QFrame()
        main_panel.setObjectName("MainPanel")
        panel_layout = QtWidgets.QVBoxLayout(main_panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(18)

        self.banner_label = ScrollingLabel()
        self.banner_label.setObjectName("BannerLabel")
        self.banner_label.set_message("Control Panel", scroll=False)
        panel_layout.addWidget(self.banner_label)

        self._apply_soft_shadow(
            self.banner_label,
            QtGui.QColor(92, 118, 255, 110),
            blur=26,
            y_offset=14,
        )

        self.character_combo = QtWidgets.QComboBox()
        self.character_combo.addItem("Loading characters...")
        panel_layout.addWidget(self.character_combo)

        button_row = QtWidgets.QHBoxLayout()
        button_row.setSpacing(16)
        self.farm_button = QtWidgets.QPushButton("Farm")
        self._apply_soft_shadow(
            self.farm_button,
            QtGui.QColor(90, 120, 255, 160),
            blur=30,
            y_offset=16,
        )
        button_row.addWidget(self.farm_button)

        self.pause_button = QtWidgets.QPushButton("Pause")
        self.pause_button.setObjectName("PauseButton")
        self.pause_button.setEnabled(False)
        self.pause_button.setToolTip("Pause farming (F5)")
        self._apply_soft_shadow(
            self.pause_button,
            QtGui.QColor(120, 210, 235, 150),
            blur=30,
            y_offset=16,
        )
        button_row.addWidget(self.pause_button)
        button_row.addStretch()
        panel_layout.addLayout(button_row)

        options_row = QtWidgets.QHBoxLayout()
        options_row.setSpacing(18)
        self.empty_checkbox = QtWidgets.QCheckBox("Empty Character")
        self.empty_checkbox.setChecked(constants.EMPTY_CHARS)
        options_row.addWidget(self.empty_checkbox)
        self.shutdown_checkbox = QtWidgets.QCheckBox("Shutdown")
        self.shutdown_checkbox.setChecked(constants.SHUTDOWN)
        options_row.addWidget(self.shutdown_checkbox)
        options_row.addStretch()
        panel_layout.addLayout(options_row)

        stats_row = QtWidgets.QHBoxLayout()
        stats_row.setSpacing(18)
        self.farmed_today_pill = QtWidgets.QLabel("Farmed Today: No")
        self.farmed_today_pill.setObjectName("StatPill")
        self.farmed_today_pill.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.farmed_today_pill.setProperty("state", "negative")
        stats_row.addWidget(self.farmed_today_pill)

        self.farm_count_pill = QtWidgets.QLabel("Runs Since Empty: 0")
        self.farm_count_pill.setObjectName("StatPill")
        self.farm_count_pill.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.farm_count_pill.setProperty("state", "neutral")
        stats_row.addWidget(self.farm_count_pill)
        stats_row.addStretch()
        panel_layout.addLayout(stats_row)

        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setObjectName("StatusMessage")
        self.status_label.setWordWrap(True)
        panel_layout.addWidget(self.status_label)

        content_layout.addWidget(main_panel, 1)

        self.status_bar = StatusBar(self._content_frame)
        content_layout.addWidget(self.status_bar, 0)

    def _apply_soft_shadow(
        self,
        widget: QtWidgets.QWidget,
        color: QtGui.QColor,
        blur: int = 28,
        y_offset: int = 12,
    ) -> None:
        effect = QtWidgets.QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(blur)
        effect.setOffset(0, y_offset)
        effect.setColor(color)
        widget.setGraphicsEffect(effect)

    def _connect_signals(self) -> None:
        self.farm_button.clicked.connect(self._on_farm_clicked)
        self.pause_button.clicked.connect(self._toggle_pause)
        self.character_combo.currentTextChanged.connect(self._on_character_selected)
        self.empty_checkbox.stateChanged.connect(self._handle_empty_checkbox)
        self.shutdown_checkbox.stateChanged.connect(self._handle_shutdown_checkbox)

        self.controller.status_changed.connect(self.status_label.setText)
        self.controller.pause_state_changed.connect(self._on_pause_state_changed)
        self.controller.farming_started.connect(self._on_farming_started)
        self.controller.farming_completed.connect(self._on_farming_completed)
        self.controller.character_progress.connect(self._on_character_progress)
        self.characters_loaded.connect(self._populate_characters)

    def _load_characters_async(self) -> None:
        def worker() -> None:
            try:
                characters = tasks.get_character_list()
            except Exception:
                characters = []
            self.characters_loaded.emit(characters)

        Thread(target=worker, daemon=True).start()

    def _populate_characters(self, characters: list[str]) -> None:
        names = [name for name in characters if isinstance(name, str) and name]
        self.character_combo.blockSignals(True)
        self.character_combo.clear()
        if not names:
            self.character_combo.addItem("No characters found")
            self.character_combo.setEnabled(False)
            self.status_label.setText("Unable to load characters from the API.")
            self._set_remaining_characters(0)
        else:
            self.character_combo.addItem("Select a Character")
            for name in names:
                self.character_combo.addItem(name)
            self.character_combo.setEnabled(True)
            self.status_label.setText(f"Loaded {len(names)} characters.")
            self._set_remaining_characters(len(names))
        self.character_combo.blockSignals(False)
        self._refresh_stats_display()
        self._schedule_state_save()

    def _is_character_farmed_today(self, name: str) -> bool:
        if not name:
            return False
        record = self._app_state.farmed_characters.get(name)
        if not isinstance(record, dict):
            return False
        return record.get("reset_key") == self._current_reset_key()

    def _characters_farmed_today_count(self) -> int:
        current_key = self._current_reset_key()
        return sum(
            1
            for record in self._app_state.farmed_characters.values()
            if isinstance(record, dict) and record.get("reset_key") == current_key
        )

    def _set_remaining_characters(self, total: int) -> None:
        self._total_characters = max(0, total)
        farmed_today = self._characters_farmed_today_count()
        self._remaining_characters = max(0, self._total_characters - farmed_today)
        self._app_state.last_total_characters = self._total_characters
        self._app_state.last_remaining_characters = self._remaining_characters

    def _utc_timestamp(self) -> str:
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def _current_reset_key(self) -> str:
        now_local = datetime.now(self._reset_tz)
        reset_time = now_local.replace(hour=2, minute=0, second=0, microsecond=0)
        if now_local < reset_time:
            reset_time -= timedelta(days=1)
        return reset_time.date().isoformat()

    def _prune_stale_farmed_characters(self) -> None:
        current_key = self._current_reset_key()
        stale = [
            name
            for name, record in self._app_state.farmed_characters.items()
            if not isinstance(record, dict) or record.get("reset_key") != current_key
        ]
        for name in stale:
            self._app_state.farmed_characters.pop(name, None)
        if stale:
            retained_total = max(0, self._app_state.last_total_characters)
            farmed_today = self._characters_farmed_today_count()
            self._app_state.last_remaining_characters = max(
                0, retained_total - farmed_today
            )

    def _handle_empty_checkbox(self, state: int) -> None:
        enabled = state == QtCore.Qt.CheckState.Checked
        self.controller.set_empty_chars_enabled(enabled)

    def _handle_shutdown_checkbox(self, state: int) -> None:
        enabled = state == QtCore.Qt.CheckState.Checked
        self.controller.set_shutdown_enabled(enabled)

    def _on_farm_clicked(self) -> None:
        self.controller.run_alt_char_farm(
            should_skip_character=self._is_character_farmed_today
        )

    def _on_farming_started(self) -> None:
        self.farm_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.pause_button.setText("Pause")
        self.pause_button.setToolTip("Pause farming (F5)")
        self.setFocus()

    def _on_farming_completed(self, payload: dict) -> None:
        self.farm_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.pause_button.setText("Pause")
        self.pause_button.setToolTip("Pause farming (F5)")

        if payload.get("error"):
            return

        characters_farmed = int(payload.get("characters_farmed", 0) or 0)
        if characters_farmed > 0:
            self._app_state.last_farm_date = date.today().isoformat()
        self._app_state.characters_farmed_last_run = characters_farmed

        if payload.get("emptied"):
            timestamp = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
            self._app_state.last_empty_timestamp = timestamp
            self._app_state.farm_count_since_empty = 0
        elif characters_farmed > 0:
            self._app_state.farm_count_since_empty = (
                max(0, self._app_state.farm_count_since_empty) + 1
            )

        if payload.get("stopped_due_to_repeats"):
            self.status_label.setText(
                "Stopped early after encountering three characters already farmed today."
            )

        self._refresh_stats_display()
        self._schedule_state_save()

    def _on_pause_state_changed(self, paused: bool) -> None:
        if not self.controller.is_farming_active():
            self.pause_button.setText("Pause")
            self.pause_button.setToolTip("Pause farming (F5)")
            self.pause_button.setEnabled(False)
            return
        if paused:
            self.pause_button.setText("Resume")
            self.pause_button.setToolTip("Resume farming (F5)")
        else:
            self.pause_button.setText("Pause")
            self.pause_button.setToolTip("Pause farming (F5)")

    def _toggle_pause(self) -> None:
        if not self.controller.is_farming_active():
            return
        self.controller.toggle_pause()

    def _create_global_hotkey(self):
        if _F5Hotkey is None or sys.platform != "win32":
            return None
        try:
            hotkey = _F5Hotkey(self)
        except Exception:
            return None
        hotkey.triggered.connect(self._toggle_pause)
        return hotkey

    def _on_character_progress(self, payload: dict) -> None:
        name_raw = payload.get("name")
        name = str(name_raw).strip() if name_raw else ""
        if not name:
            return

        status = str(payload.get("status") or "").lower()
        current_key = self._current_reset_key()

        if status == "farmed":
            self._app_state.farmed_characters[name] = {
                "reset_key": current_key,
                "timestamp": self._utc_timestamp(),
            }
        elif (
            status == "skipped-already"
            and name not in self._app_state.farmed_characters
        ):
            self._app_state.farmed_characters[name] = {
                "reset_key": current_key,
                "timestamp": None,
            }

        self._set_remaining_characters(self._total_characters)
        remaining = self._remaining_characters
        total = self._total_characters

        if status == "farmed":
            emptied = bool(payload.get("emptied"))
            suffix = " and emptied" if emptied else ""
            self.status_label.setText(
                f"{name} farmed{suffix}. {remaining} of {total} remaining."
            )
        elif status == "skipped-already":
            self.status_label.setText(
                f"{name} already farmed this reset. {remaining} of {total} remaining."
            )
        else:
            self.status_label.setText(f"{name}: {payload.get('status', 'updated')}")

        self._refresh_stats_display()
        self._schedule_state_save()

    def _on_character_selected(self, name: str) -> None:
        if name in {
            "",
            "Loading characters...",
            "Select a Character",
            "No characters found",
        }:
            return
        self.status_label.setText(f"Character {name} selected")
        self.banner_label.set_message(f"Character {name} selected", scroll=True)
        self.controller.lookup_character(name)

    def _start_event_timer(self) -> None:
        self._event_timer = QtCore.QTimer(self)
        self._event_timer.timeout.connect(self._refresh_event_banner)
        self._event_timer.start(60000)
        self._refresh_event_banner()

    def _refresh_event_banner(self) -> None:
        event_text = self.controller.copy_next_event_code()
        if event_text:
            self.banner_label.set_message(event_text, scroll=True, duration=20.0)
        else:
            self.banner_label.set_message("Control Panel", scroll=False)

    def _start_uptime_timer(self) -> None:
        self._uptime_timer = QtCore.QTimer(self)
        self._uptime_timer.timeout.connect(self._update_uptime)
        self._uptime_timer.start(1000)
        self._update_uptime()

    def _update_uptime(self) -> None:
        elapsed = int(time.monotonic() - self._app_start_time)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.status_bar.set_uptime(f"Uptime {hours:02}:{minutes:02}:{seconds:02}")

    def _refresh_stats_display(self) -> None:
        farmed_today = self._characters_farmed_today_count() > 0
        farm_text = "Farmed Today: Yes" if farmed_today else "Farmed Today: No"
        farm_state = "positive" if farmed_today else "negative"
        self._set_pill_state(self.farmed_today_pill, farm_text, farm_state)
        if self._app_state.last_farm_date:
            self.farmed_today_pill.setToolTip(
                f"Last farm date: {self._app_state.last_farm_date}"
            )
        else:
            self.farmed_today_pill.setToolTip("No farming sessions recorded yet.")

        runs = max(0, self._app_state.farm_count_since_empty)
        unique_today = self._characters_farmed_today_count()
        runs_text = f"Runs Since Empty: {runs}"
        runs_state = "info" if runs else "neutral"
        self._set_pill_state(self.farm_count_pill, runs_text, runs_state)

        tooltip_parts: List[str] = []
        if self._app_state.last_empty_timestamp:
            tooltip_parts.append(
                f"Last emptied: {self._app_state.last_empty_timestamp}"
            )
        if self._app_state.characters_farmed_last_run:
            tooltip_parts.append(
                f"Previous run farmed {self._app_state.characters_farmed_last_run} characters"
            )
        tooltip_parts.append(f"Characters farmed today: {unique_today}")
        self.farm_count_pill.setToolTip(
            " | ".join(tooltip_parts) if tooltip_parts else "No emptying recorded yet."
        )

    def _set_pill_state(self, label: QtWidgets.QLabel, text: str, state: str) -> None:
        label.setText(text)
        label.setProperty("state", state)
        label.style().unpolish(label)
        label.style().polish(label)
        label.update()

    def _schedule_state_save(self) -> None:
        self._save_state_timer.start(750)

    def _persist_state(self) -> None:
        self._save_state_timer.stop()
        persistence.save_app_state(self._app_state)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:  # type: ignore[override]
        if event.key() == QtCore.Qt.Key.Key_F5:
            self._toggle_pause()
            event.accept()
            return
        super().keyPressEvent(event)

    def showEvent(self, event: QtGui.QShowEvent) -> None:  # type: ignore[override]
        super().showEvent(event)
        if self._global_hotkey is not None and not self._global_hotkey.is_registered:
            if not self._global_hotkey.register():
                self.status_label.setText(
                    "Global F5 hotkey unavailable; using in-app shortcut only."
                )

    def moveEvent(self, event: QtGui.QMoveEvent) -> None:  # type: ignore[override]
        super().moveEvent(event)
        top_left = self.frameGeometry().topLeft()
        self._app_state.window_x = int(top_left.x())
        self._app_state.window_y = int(top_left.y())
        self._schedule_state_save()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        size = event.size()
        self._app_state.window_width = int(size.width())
        self._app_state.window_height = int(size.height())
        self._schedule_state_save()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # type: ignore[override]
        if hasattr(self, "_global_hotkey") and self._global_hotkey is not None:
            self._global_hotkey.dispose()
            self._global_hotkey = None
        self._persist_state()
        super().closeEvent(event)


def create_window() -> MainWindow:
    return MainWindow()
