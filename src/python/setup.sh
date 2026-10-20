#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$HOME/.ci"

# The memory backend requires a 64-bit Python; stop before creating anything.
if ! python3 -c 'import struct, sys; sys.exit(struct.calcsize("P") * 8 != 64)' 2>/dev/null; then
    echo "ERROR: creating-intelligence requires a 64-bit Python 3."
    echo "Found: $(command -v python3 || echo 'no python3 on PATH')"
    exit 1
fi

if ! command -v dot &> /dev/null; then
    echo "======================================================================"
    echo " "
    echo "WARNING: Graphviz ('dot') was not found."
    echo "Circuit diagrams will use a fallback layout instead of the"
    echo "left-to-right layout. Everything else works normally."
    echo " "
    echo "To enable the left-to-right layout, install Graphviz:"
    echo "  - macOS:         brew install graphviz"
    echo "  - Ubuntu/Debian: sudo apt-get install graphviz"
    echo "  - Fedora:        sudo dnf install graphviz"
    echo "  - Arch:          sudo pacman -S graphviz"
    echo " "
    echo "======================================================================"
fi

# Create virtual environment outside iCloud sync directory if not present
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment at $VENV_PATH..."
    python3 -m venv "$VENV_PATH"
fi

source "$VENV_PATH/bin/activate"

# Remove compiled memory libraries left by earlier builds. The loader tries
# version-specific names (libmemory.cpython-314-darwin.so) before the plain
# libmemory.so that setup.py builds, so a stale library from an older build
# would shadow the fresh one and fail on renamed or new C functions.
PKG_DIR="$SCRIPT_DIR/creating_intelligence"
find "$PKG_DIR" -maxdepth 1 -type f -name 'libmemory*' \
    \( -name '*.so' -o -name '*.dylib' -o -name '*.pyd' \) \
    -print -delete | sed 's/^/Removed stale library: /'

echo "Installing creating-intelligence package..."
python -m pip install -q --upgrade pip
python -m pip install -q -e "$SCRIPT_DIR[viz]"

# A failed C compile no longer stops the install, so check which backend loads.
BACKEND=$(env -u MEMORY_BACKEND python -W ignore -c \
    "import creating_intelligence as ci; print(ci.backend)")

if [ "$BACKEND" != "c_ffi" ]; then
    echo "======================================================================"
    echo " "
    echo "WARNING: The C memory backend could not be built or loaded."
    echo "creating-intelligence works, but uses the slower pure-Python backend."
    echo " "
    echo "Reason:"
    MEMORY_BACKEND=c_ffi python -c "import creating_intelligence" 2>&1 \
        | tail -n 1 | sed 's/^/  /' || true
    echo " "
    echo "If no library was found, install a C compiler and rerun this script:"
    echo "  - macOS:         xcode-select --install"
    echo "  - Ubuntu/Debian: sudo apt-get install build-essential python3-dev"
    echo "  - Fedora:        sudo dnf groupinstall \"Development Tools\" && sudo dnf install python3-devel"
    echo "  - Arch:          sudo pacman -S base-devel"
    echo " "
    echo "======================================================================"
fi

echo "Setup complete (memory backend: $BACKEND). Activate with: source \"$VENV_PATH/bin/activate\""
