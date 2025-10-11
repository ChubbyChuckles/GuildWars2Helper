#!/usr/bin/env sh
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${ROOT_DIR}/include/nuklear.h"
URL_CORE="https://raw.githubusercontent.com/Immediate-Mode-UI/Nuklear/master/src/nuklear.h"
URL_GLFW="https://raw.githubusercontent.com/Immediate-Mode-UI/Nuklear/master/demo/glfw_opengl2/nuklear_glfw_gl2.h"

echo "Saved Nuklear to $TARGET"
if [ ! -f "$TARGET" ]; then
    echo "Downloading Nuklear core..."
    curl -L "$URL_CORE" -o "$TARGET"
else
    echo "nuklear.h already present at $TARGET"
fi

if [ ! -f "${ROOT_DIR}/include/nuklear_glfw_gl2.h" ]; then
    echo "Downloading Nuklear GLFW helper..."
    curl -L "$URL_GLFW" -o "${ROOT_DIR}/include/nuklear_glfw_gl2.h"
else
    echo "nuklear_glfw_gl2.h already present"
fi

echo "Nuklear headers ready in ${ROOT_DIR}/include"
