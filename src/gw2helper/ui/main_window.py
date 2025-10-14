"""PyQt6 user interface for the Guild Wars 2 helper automation."""

from __future__ import annotations

import time
from threading import Thread
from typing import List, Optional

from PyQt6 import QtCore, QtGui, QtWidgets

from .. import constants
from ..automation import tasks
from ..controllers.task_controller import TaskController


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
        self.min_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.min_button.setToolTip("Minimize")
        self.min_button.clicked.connect(self._on_minimize)
        layout.addWidget(self.min_button)

        self.close_button = QtWidgets.QToolButton()
        self.close_button.setObjectName("TitleBarButton")
        self.close_button.setText("✕")
        self.close_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
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
        self._app_start_time = time.monotonic()
        self.controller = TaskController()
        self._setup_window()
        self._build_ui()
        self._connect_signals()
        self._load_characters_async()
        self._start_event_timer()
        self._start_uptime_timer()

    def _setup_window(self) -> None:
        flags = (
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.Window
            | QtCore.Qt.WindowType.WindowSystemMenuHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowFlags(flags)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.resize(520, 460)
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

        self.bug_button = QtWidgets.QPushButton("Bug")
        self._apply_soft_shadow(
            self.bug_button,
            QtGui.QColor(214, 92, 220, 150),
            blur=30,
            y_offset=16,
        )
        button_row.addWidget(self.bug_button)
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
        self.farm_button.clicked.connect(self.controller.run_alt_char_farm)
        self.bug_button.clicked.connect(self.controller.run_skyscale_bug)
        self.character_combo.currentTextChanged.connect(self._on_character_selected)
        self.empty_checkbox.stateChanged.connect(self._handle_empty_checkbox)
        self.shutdown_checkbox.stateChanged.connect(self._handle_shutdown_checkbox)

        self.controller.status_changed.connect(self.status_label.setText)
        self.characters_loaded.connect(self._populate_characters)

    def _handle_empty_checkbox(self, state: int) -> None:
        enabled = state == QtCore.Qt.CheckState.Checked
        self.controller.set_empty_chars_enabled(enabled)

    def _handle_shutdown_checkbox(self, state: int) -> None:
        enabled = state == QtCore.Qt.CheckState.Checked
        self.controller.set_shutdown_enabled(enabled)

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
        self.character_combo.blockSignals(True)
        self.character_combo.clear()
        if not characters:
            self.character_combo.addItem("No characters found")
        else:
            self.character_combo.addItem("Select a Character")
            for name in characters:
                self.character_combo.addItem(name)
        self.character_combo.blockSignals(False)

    def _on_character_selected(self, name: str) -> None:
        if name in {"", "Loading characters...", "Select a Character", "No characters found"}:
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
        self.status_bar.set_uptime(
            f"Uptime {hours:02}:{minutes:02}:{seconds:02}"
        )


def create_window() -> MainWindow:
    return MainWindow()
