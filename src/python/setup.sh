#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The virtual environment must be in a location that's not iCloud-synched.
# Activate with: source ~/.ci/bin/activate
VENV_PATH="$HOME/.ci"

if [ -d "$VENV_PATH" ]; then
    echo "Removing existing virtual environment..."
    rm -rf "$VENV_PATH"
fi

echo "Cleaning build artifacts and cache..."
rm -rf "$SCRIPT_DIR/creating_intelligence.egg-info"
find "$SCRIPT_DIR" -type d -name "__pycache__" -exec rm -rf {} +

echo "Creating virtual environment at $VENV_PATH..."
python3 -m venv "$VENV_PATH"

echo "Building C backend..."
make -C ../c/


source "$VENV_PATH/bin/activate"
echo "Building creating-intelligence package..."
pip install --upgrade pip
pip install --force-reinstall -e "$SCRIPT_DIR"

echo "Setup complete. Run 'source \"$VENV_PATH/bin/activate\"' to start."