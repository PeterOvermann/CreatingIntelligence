#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Clean previous build artifacts to prevent uploading stale or unwanted files
rm -rf "$SCRIPT_DIR/dist"

# Create a secure temporary directory outside of iCloud-synced paths
TEMP_DIR=$(mktemp -d)
VENV_PATH="$TEMP_DIR/.build_venv"

# Guarantee cleanup of the temporary directory upon exit
trap 'rm -rf "$TEMP_DIR"' EXIT

# Create and activate a fresh isolated environment
python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"

python3 -m pip install -q --upgrade pip build twine

# Check for Graphviz once and export the flag for all setup.py subprocesses
if ! command -v dot &> /dev/null; then
    echo -e "\n============================================================"
    echo "WARNING: Graphviz ('dot') is required for advanced circuit schematics but was not found."
    echo "The package will install normally, but visualization features will use a fallback layout."
    echo "Please install Graphviz manually if needed:"
    echo "  - Windows: winget install Graphviz.Graphviz"
    echo "  - macOS: brew install graphviz"
    echo "  - Ubuntu/Debian: sudo apt-get install graphviz"
    echo "  - Fedora: sudo dnf install graphviz"
    echo "  - Arch: sudo pacman -S graphviz"
    echo -e "============================================================\n"
fi
export _CI_GRAPHVIZ_WARN_SHOWN="1"

cd "$SCRIPT_DIR"
python3 -m build --sdist > /dev/null