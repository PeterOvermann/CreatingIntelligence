#!/bin/bash
set -e

if ! command -v dot &> /dev/null; then
    echo "============================================================"
    echo "WARNING: Graphviz ('dot') is required for advanced circuit schematics but was not found."
    echo "The package will install normally, but visualization features will use a fallback layout."
    echo "Please install Graphviz manually if needed:"
    echo "  - macOS: brew install graphviz"
    echo "  - Ubuntu/Debian: sudo apt-get install graphviz"
    echo "  - Fedora: sudo dnf install graphviz"
    echo "  - Arch: sudo pacman -S graphviz"
    echo "============================================================"
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
pip install -q --upgrade pip
pip install -q -e "$SCRIPT_DIR"

echo "Setup complete. Activate with: source \"$VENV_PATH/bin/activate\""