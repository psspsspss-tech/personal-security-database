#!/usr/bin/env bash
# ==============================================================================
# Personal Security Suite — Launcher Script (Linux)
# ==============================================================================

# ANSI Color Codes for Rich Terminal Aesthetics
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Set terminal title
echo -ne "\033]0;Personal Security Suite — Launcher\007"

# Get current script directory
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo -e "\n${BLUE}=======================================================${NC}"
echo -e "${CYAN}${BOLD}          Personal Security Command Center             ${NC}"
echo -e "${BLUE}=======================================================${NC}\n"

# Function to safely check and release ports
kill_port() {
    local port=$1
    echo -e "  [*] Checking for existing server on port ${CYAN}$port${NC}..."
    
    local pid=""
    if command -v lsof &> /dev/null; then
        pid=$(lsof -t -i:$port 2>/dev/null)
    elif command -v fuser &> /dev/null; then
        pid=$(fuser $port/tcp 2>/dev/null | awk '{print $1}')
    else
        pid=$(ss -lntp "sport = :$port" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | head -n 1)
    fi

    if [ -n "$pid" ]; then
        echo -e "  ${YELLOW}[*] Stopping old server (PID $pid)...${NC}"
        kill -9 $pid >/dev/null 2>&1
    fi
}

# Kill any old processes on ports 8767 and 8768
kill_port 8767
kill_port 8768
sleep 1

# Check Python installation
if command -v python3 &> /dev/null; then
    PYTHON_EXE="python3"
elif command -v python &> /dev/null; then
    PYTHON_EXE="python"
else
    echo -e "  ${RED}[ERROR] Python is not installed or not in PATH.${NC}"
    echo -e "  Please install Python 3.9+ from your distribution package manager."
    echo -e "  Example: sudo apt install python3 python3-pip\n"
    exit 1
fi
echo -e "  ${GREEN}[OK]${NC} Python found ($($PYTHON_EXE --version | head -n 1))."

# Verify dependencies
echo -e "  [*] Verifying Python dependencies..."
if ! $PYTHON_EXE -m pip install -r "$SCRIPT_DIR/backend/requirements.txt" --quiet --disable-pip-version-check 2>/dev/null; then
    # Retry with --break-system-packages in case of PEP 668 restrictions
    $PYTHON_EXE -m pip install -r "$SCRIPT_DIR/backend/requirements.txt" --quiet --disable-pip-version-check --break-system-packages 2>/dev/null
fi
echo -e "  ${GREEN}[OK]${NC} Dependencies ready."

# Get Local IP
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP=$(ip route get 1.0.0.0 2>/dev/null | awk '{print $7}')
fi
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP="127.0.0.1"
fi

echo -e "\n${BLUE}=======================================================${NC}"
echo -e "  ${BOLD}Dashboard URLs:${NC}"
echo -e "    This PC  :  ${GREEN}https://127.0.0.1:8767${NC}"
echo -e "    Network  :  ${GREEN}https://${LOCAL_IP}:8767${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo -e "  Scan the QR code in the dashboard to open on mobile"
echo -e "${BLUE}=======================================================${NC}\n"
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop the server.\n"

# Launch server and browser
cd "$SCRIPT_DIR/backend"
sleep 2

# Check if Graphical environment is active before opening browser
if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
    if command -v xdg-open &> /dev/null; then
        xdg-open "https://127.0.0.1:8767" >/dev/null 2>&1 &
    elif command -v sensible-browser &> /dev/null; then
        sensible-browser "https://127.0.0.1:8767" >/dev/null 2>&1 &
    fi
fi

$PYTHON_EXE server.py
