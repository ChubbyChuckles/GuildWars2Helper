"""Setup script for building MSI installers via cx_Freeze."""

from __future__ import annotations

import sys
from pathlib import Path

from cx_Freeze import Executable, setup

ROOT_DIR = Path(__file__).parent.resolve()
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

_build_path = []
for entry in [str(SRC_DIR), *sys.path]:
    if entry and entry not in _build_path:
        _build_path.append(entry)

try:
    import importlib

    importlib.import_module("gw2helper.ui.main_window")
except Exception as exc:  # pragma: no cover - packaging sanity check
    raise RuntimeError(
        "Failed to import 'gw2helper.ui.main_window'. Ensure the src directory is on sys.path and "
        "all runtime dependencies (e.g., PyQt6) are installed."
    ) from exc

try:
    import cv2  # type: ignore[import-not-found]

    # cx_Freeze treats every submodule declared in cv2 as a package; the compiled
    # extension `cv2.gapi.wip` lacks a `__path__`, so we provide a dummy one to
    # keep the ModuleFinder happy during the freeze step.
    gapi = getattr(cv2, "gapi", None)
    if gapi is not None:
        wip = getattr(gapi, "wip", None)
        if wip is not None and not hasattr(wip, "__path__"):
            setattr(wip, "__path__", [])
except ModuleNotFoundError:
    pass

build_exe_options = {
    "packages": ["gw2helper"],
    "includes": ["gw2helper.ui.main_window"],
    "include_files": [(".env.example", ".env.example")],
    "path": _build_path,
}

setup(
    name="GuildWars2Helper",
    version="0.1.0",
    description="Guild Wars 2 helper automation UI",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            script="src/main.py",
            base="Win32GUI",
            target_name="GuildWars2Helper.exe",
        )
    ],
)
