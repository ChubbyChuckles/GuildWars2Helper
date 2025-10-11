# Dependency Scripts

These helper scripts download third-party dependencies used by the project.

## GLFW

- `fetch_glfw.sh`: POSIX shell script for Linux/macOS.
- `fetch_glfw.ps1`: PowerShell script for Windows.

The scripts download the requested GLFW release (default `3.4`) into `scripts/deps/glfw` and leave the source tree intact. The `Makefile` automatically uses the downloaded path when building statically. Remove the `scripts/deps` directory to re-run the download from scratch.
