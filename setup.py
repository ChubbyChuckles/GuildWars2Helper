"""Setup script for building MSI installers via cx_Freeze."""

from __future__ import annotations

from cx_Freeze import Executable, setup

build_exe_options = {
    "packages": ["gw2helper", "PyQt6"],
    "includes": [],
    "include_files": [],
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
