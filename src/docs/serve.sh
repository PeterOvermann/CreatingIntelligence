#!/bin/bash

# Navigate to the directory where this script is located
cd "$(dirname "$0")/../../docs/" || exit 1

PORT=8000

# Check if the port is in use and aggressively kill the blocking process
BLOCKING_PID=$(lsof -Pi :$PORT -sTCP:LISTEN -t)

if [ -n "$BLOCKING_PID" ]; then
    echo "Port $PORT is currently occupied by PID $BLOCKING_PID. Terminating it..."
    kill -9 $BLOCKING_PID
    # Give the operating system a brief moment to fully release the network port
    sleep 1
fi

# Define a cleanup function to gracefully kill the new server when we exit
cleanup() {
    trap - EXIT
    echo ""
    echo "Shutting down web server (PID: $SERVER_PID)..."
    kill $SERVER_PID 2>/dev/null
    exit 0
}

# Catch exit signals (Terminal close, Ctrl+C) and run the cleanup function
trap cleanup EXIT INT TERM

# Start the Python web server in the background
echo "Starting web server on http://localhost:$PORT..."
python3 -m http.server $PORT &
SERVER_PID=$!

# Wait a brief moment to ensure the server has fully started
sleep 1

# Open the local URL in Google Chrome (or default browser as a fallback)
open -a "Google Chrome" "http://localhost:$PORT" || open "http://localhost:$PORT"

# Keep the script running in the foreground
echo "Server is running. Press Ctrl+C or close this Terminal window to shut it down."
wait $SERVER_PID
