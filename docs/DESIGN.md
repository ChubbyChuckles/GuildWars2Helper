# Architectural Overview

This document outlines the high-level architecture of the GuildWars2Helper futuristic control panel application.

## Goals

- Provide a clean separation between UI logic, rendering, and utility concerns.
- Keep the dependency footprint minimal while enabling cross-platform builds.
- Ensure future maintainability by following modular C99 patterns.

## Modules

### Entry Point (`src/main.c`)

- Initializes the logger, renderer, and GUI layers.
- Runs the main loop while forwarding events into Nuklear.
- Coordinates shutdown to ensure resources are released in order.

### GUI Layer (`src/gui`)

- Wraps all Nuklear immediate-mode UI code.
- Exposes a small API:
  - `gui_init` for creating the Nuklear context, fonts, and styling.
  - `gui_render` for building the frame contents based on application state.
  - `gui_shutdown` for releasing UI resources.
- Applies a dark futuristic theme and builds the control panel, storing UI state in a dedicated struct passed into each call.

### Renderer Layer (`src/render`)

- Abstracts GLFW and OpenGL operations.
- Responsibilities:
  - Create and manage the window/context lifecycle.
  - Bridge input events into Nuklear's GLFW backend helpers.
  - Provide frame boundaries via `render_begin_frame` and `render_end_frame`.
- Keeps platform-specific handling inside GLFW, maintaining portability.

### Utilities (`src/utils`)

- Currently contains a minimal logging system with severity levels and timestamping support.
- Designed for easy extension (e.g., configuration loader, metrics helpers).

### Tests (`tests`)

- Includes a minimal custom testing harness.
- Validates the logging module to ensure the foundational utility layer behaves correctly.

## Data Flow

```
main.c
  ├─ renderer_init
  │    └─ glfw + OpenGL setup
  ├─ gui_init
  │    └─ Nuklear context + fonts + theme
  └─ main loop
       ├─ renderer_pump_events
       ├─ render_begin_frame
       ├─ gui_render
       └─ render_end_frame
```

## Concurrency

- The sample application remains single-threaded for simplicity.
- If future features require background tasks (e.g., network polling), they should communicate with the GUI through thread-safe queues, decoupling rendering from data ingestion.

## Future Extensions

- Add configuration-driven panels sourced from JSON files.
- Integrate service APIs from Guild Wars 2 for live data.
- Introduce automated tests for GUI state machines using headless rendering.
- Expand logging to support sinks such as files or remote telemetry.
