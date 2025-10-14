"""Legacy entry point that proxies to the PyQt6 application."""

from __future__ import annotations

import pathlib
import sys

_SRC_DIR = pathlib.Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from gw2helper.app import main


def run() -> int:
    """Launch the PyQt6 application and return its exit code."""
    return main()


if __name__ == "__main__":
    raise SystemExit(run())
