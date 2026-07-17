#!/usr/bin/env bash
# ==============================================================================
# Personal Security Suite — Background Loop (Linux)
# ==============================================================================

# Get current script directory
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Check Python installation
if command -v python3 &> /dev/null; then
    PYTHON_EXE="python3"
else
    PYTHON_EXE="python"
fi

# Infinite loop to keep server alive
while true; do
    echo "  [*] Launching master.py..."
    $PYTHON_EXE master.py
    echo ""
    echo "  [!] Server stopped. Restarting in 5 seconds..."
    sleep 5
done
