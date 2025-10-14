"""Application entry point for the PyQt6 Guild Wars 2 helper."""

from __future__ import annotations

import sys

from PyQt6 import QtWidgets

from .ui.main_window import create_window


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    window = create_window()
    window.show()
    return app.exec()
