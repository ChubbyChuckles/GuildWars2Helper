# GuildWars2Helper Futuristic Control Panel

GuildWars2Helper is a cross-platform desktop application scaffold built with C99, Nuklear, GLFW, and OpenGL. It demonstrates a futuristic-styled control panel UI with neon accents, modular architecture, and a minimal dependency footprint.

## Features

- Strict C99 codebase with clean modular structure.
- Immediate-mode GUI powered by Nuklear with custom dark neon theming.
- GLFW + OpenGL render backend wrapped in a reusable renderer module.
- Simple logging utilities and unit tests.
- Portable Makefile supporting Linux, macOS, and Windows builds.

## Project Layout

```
.
├── assets/                     # Static assets (fonts, screenshots)
├── build/                      # Build artifacts (ignored)
├── docs/                       # Documentation (e.g., DESIGN.md)
├── include/                    # External headers (Nuklear, GLFW)
├── scripts/                    # Dependency helper scripts
├── src/                        # Application sources
│   ├── gui/                    # Nuklear UI composition and styling
│   ├── render/                 # GLFW/OpenGL renderer backend
│   └── utils/                  # Shared utilities (logging)
├── tests/                      # Minimal C99 unit tests
├── LICENSE                     # MIT License
└── README.md
```

## Prerequisites

- C compiler supporting C99 (`gcc`, `clang`, or MSVC with `cl` and `/std:c11`).
- Build tools: `make`, `git`, `curl`, and `cmake` (for fetching GLFW).
- OpenGL 3.3 capable GPU/driver.
- For Windows: install `mingw-w64` or Visual Studio Build Tools and ensure `make` is available (e.g., via MSYS2).

## Getting Started

1. **Fetch dependencies**

   Nuklear headers are fetched automatically during the first build via
   `scripts/fetch_nuklear.*`. GLFW is downloaded on demand via the helper
   script. Run one of:

   ```sh
   # Linux/macOS
   ./scripts/fetch_glfw.sh

   # Windows (PowerShell)
   pwsh scripts/fetch_glfw.ps1
   ```

   The script places GLFW under `scripts/deps/glfw`.

2. **Build the project**

   ```sh
   make
   ```

   Executable is placed in `build/bin/gw2helper` (or `gw2helper.exe` on Windows).

3. **Run the sample**

   ```sh
   ./build/bin/gw2helper    # Linux/macOS
   .\build\bin\gw2helper.exe  # Windows
   ```

4. **Execute tests**

   ```sh
   make test
   ```

## Assets

- Place a sci-fi styled TTF font (e.g., [Orbitron](https://fonts.google.com/specimen/Orbitron)) in `assets/Orbitron-Regular.ttf`.
- Optionally add a screenshot under `assets/screenshots/futuristic-panel.png`. Update the path in this README after capturing your UI.

## Configuration

Runtime configuration is minimal. Logging is enabled by default and prints to stdout. Toggle UI state and visuals within `src/gui/gui.c`.

## Troubleshooting

- Ensure the GLFW static or shared library is in your linker path. The fetch script builds GLFW from source; refer to `scripts/README.md` for details.
- On macOS, install dependencies via Homebrew: `brew install cmake glfw`.
- On Windows, ensure the correct Visual Studio command prompt or MSYS2 environment is used so `make` and the compiler are available.

## License

This project is licensed under the MIT License. See `LICENSE` for details.
