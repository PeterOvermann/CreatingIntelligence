#!/bin/bash
set -e

# Pre-flight check to abort cleanly before pip generates verbose errors
if ! command -v dot &> /dev/null; then
    echo "============================================================"
    echo "ERROR: Graphviz ('dot') is required but was not found."
    echo "Please install Graphviz manually:"
    echo "  - macOS: brew install graphviz"
    echo "  - Ubuntu/Debian: sudo apt-get install graphviz"
    echo "  - Fedora: sudo dnf install graphviz"
    echo "  - Arch: sudo pacman -S graphviz"
    echo "============================================================"
    exit 1
fi


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$HOME/.ci"

# Create virtual environment outside iCloud sync directory if not present
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment at $VENV_PATH..."
    python3 -m venv "$VENV_PATH"
fi

source "$VENV_PATH/bin/activate"

echo "Installing creating-intelligence package..."
pip install -qq --upgrade pip
pip install -q -e "$SCRIPT_DIR"

echo "Setup complete. Activate with: source \"$VENV_PATH/bin/activate\""
