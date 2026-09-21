#!/usr/bin/env bash

# Resolve the absolute path to the directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Navigate up one level to the web server's root directory
cd "$SCRIPT_DIR/.." || { echo "Failed to navigate to root directory"; exit 1; }

echo "Serving site at http://localhost:8000"
echo "Press Ctrl+C to stop."

# Start the server
python3 -m http.server 8000