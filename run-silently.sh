#!/usr/bin/env bash
# ==============================================================================
# Personal Security Suite — Silent Background Launcher (Linux)
# ==============================================================================

# Get current script directory
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Launch the server loop in the background and detach
nohup "$SCRIPT_DIR/server-loop.sh" > /dev/null 2>&1 &

echo -e "\n  \033[0;32m[OK]\033[0m Security Suite is running silently in the background."
echo -e "  (To stop it, run ./stop-server.sh)\n"
sleep 3
