#!/usr/bin/env sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPS_DIR="$SCRIPT_DIR/deps"
GLFW_DIR="$DEPS_DIR/glfw"
GLFW_VERSION="3.4"
GLFW_ARCHIVE="glfw-${GLFW_VERSION}.zip"
GLFW_URL="https://github.com/glfw/glfw/releases/download/${GLFW_VERSION}/${GLFW_ARCHIVE}"

if [ -d "$GLFW_DIR" ]; then
    echo "GLFW already downloaded at $GLFW_DIR"
    exit 0
fi

mkdir -p "$DEPS_DIR"
cd "$DEPS_DIR"

if [ ! -f "$GLFW_ARCHIVE" ]; then
    echo "Downloading GLFW ${GLFW_VERSION}..."
    curl -L -o "$GLFW_ARCHIVE" "$GLFW_URL"
fi

if command -v unzip >/dev/null 2>&1; then
    unzip "$GLFW_ARCHIVE"
else
    echo "Error: unzip not found. Please install unzip and rerun."
    exit 1
fi

mv "glfw-${GLFW_VERSION}" glfw

echo "GLFW extracted to $GLFW_DIR"
