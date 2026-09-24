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

cd "$SCRIPT_DIR"
python3 -m build --sdist > /dev/null