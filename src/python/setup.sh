#!/bin/bash


echo "Checking system dependencies..."
if ! command -v dot &> /dev/null; then
    echo "Graphviz (dot) could not be found."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Installing Graphviz (dot) via Homebrew..."
        brew install graphviz
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Installing Graphviz (dot) via apt..."
        sudo apt-get update && sudo apt-get install -y graphviz
    else
        echo "Cannot automatically install Graphviz (dot). Please install manually."
        exit 1
    fi
fi


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The virtual environment must be in a location that's not iCloud-synched.
# Activate with: source ~/.ci/bin/activate
VENV_PATH="$HOME/.ci"

if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment at $VENV_PATH..."
    python3 -m venv "$VENV_PATH"
else
    echo "Using existing virtual environment at $VENV_PATH..."
fi

# Only clean artifacts if a 'clean' argument is passed to the script
if [ "$1" == "clean" ]; then
    echo "Cleaning build artifacts and cache..."
    rm -rf "$SCRIPT_DIR/creating_intelligence.egg-info"
    find "$SCRIPT_DIR" -type d -name "__pycache__" -exec rm -rf {} +
fi

echo "Building C backend shared library..."
make -C "$SCRIPT_DIR/../c" lib

source "$VENV_PATH/bin/activate"
echo "Building creating-intelligence package..."
pip install -qq --upgrade pip
pip install -qq -e "$SCRIPT_DIR"

echo "Setup complete. Run 'source \"$VENV_PATH/bin/activate\"' to start."

