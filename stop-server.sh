#!/usr/bin/env bash
# ==============================================================================
# Personal Security Suite — Stop Server Script (Linux)
# ==============================================================================

# ANSI Color Codes for Rich Terminal Aesthetics
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Set terminal title
echo -ne "\033]0;Security Suite — Stopping...\007"

echo -e "\n${BLUE}=======================================================${NC}"
echo -e "${RED}             Stopping Security Suite...                ${NC}"
echo -e "${BLUE}=======================================================${NC}\n"

# 1. Remove autostart entry if present
AUTOSTART_FILE="$HOME/.config/autostart/personal-security-suite.desktop"
if [ -f "$AUTOSTART_FILE" ]; then
    echo -e "  [*] Disabling auto-start..."
    rm -f "$AUTOSTART_FILE"
    echo -e "  ${GREEN}[OK]${NC} Auto-start disabled."
fi

# 2. Terminate background loops and server scripts
echo -e "  [*] Terminating server loops and python processes..."
# Kill server-loop.sh, run-silently.sh
pkill -f "server-loop.sh" >/dev/null 2>&1
pkill -f "run-silently.sh" >/dev/null 2>&1

# Kill python processes running master.py, server.py, or agent.py
pkill -f "python.*master.py" >/dev/null 2>&1
pkill -f "python.*server.py" >/dev/null 2>&1
pkill -f "python.*agent.py" >/dev/null 2>&1

# 3. Release network ports (8765, 8766, 8767, 8768)
release_port() {
    local port=$1
    local pid=""
    if command -v lsof &> /dev/null; then
        pid=$(lsof -t -i:$port 2>/dev/null)
    elif command -v fuser &> /dev/null; then
        pid=$(fuser $port/tcp 2>/dev/null | awk '{print $1}')
    fi

    if [ -n "$pid" ]; then
        echo -e "  [*] Releasing network port ${CYAN}$port${NC} (Killing PID $pid)..."
        kill -9 $pid >/dev/null 2>&1
    fi
}

for port in 8765 8766 8767 8768; do
    release_port $port
done

echo -e "\n${BLUE}=======================================================${NC}"
echo -e "  ${GREEN}[OK]${NC} Security Suite fully stopped."
echo -e "${BLUE}=======================================================${NC}\n"
