#!/usr/bin/env bash
# ==============================================================================
# Personal Security Suite — Advanced Manager (Linux)
# ==============================================================================

# ANSI Color Codes for Rich UI
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Set terminal title
echo -ne "\033]0;Security Suite - Advanced Manager\007"

# Get current script directory
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Find python executable
if command -v python3 &> /dev/null; then
    PYTHON_EXE="python3"
elif command -v python &> /dev/null; then
    PYTHON_EXE="python"
else
    PYTHON_EXE=""
fi

# Helper to verify Python is available
check_python() {
    if [ -z "$PYTHON_EXE" ]; then
        echo -e "\n  ${RED}[ERROR] Python is not installed or not in PATH.${NC}"
        echo -e "  Please install Python 3.9+ from your distribution package manager."
        read -n 1 -s -r -p "Press any key to return to menu..."
        return 1
    fi
    return 0
}

# Function to safely check and release ports
kill_ports() {
    echo -e "  [*] Checking and clearing old server instances..."
    for port in 8765 8767 8768; do
        local pid=""
        if command -v lsof &> /dev/null; then
            pid=$(lsof -t -i:$port 2>/dev/null)
        elif command -v fuser &> /dev/null; then
            pid=$(fuser $port/tcp 2>/dev/null | awk '{print $1}')
        fi

        if [ -n "$pid" ]; then
            echo -e "  ${YELLOW}[*] Port $port is busy. Stopping old process (PID $pid)...${NC}"
            kill -9 $pid >/dev/null 2>&1
        fi
    done
    sleep 1
}

# Open URL in browser
open_browser() {
    local url=$1
    if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
        if command -v xdg-open &> /dev/null; then
            xdg-open "$url" >/dev/null 2>&1 &
        elif command -v sensible-browser &> /dev/null; then
            sensible-browser "$url" >/dev/null 2>&1 &
        else
            echo -e "  [!] Could not open browser automatically. Please open: ${GREEN}$url${NC}"
        fi
    else
        echo -e "  [!] No GUI display detected. Please open: ${GREEN}$url${NC}"
    fi
}

while true; do
    clear
    echo -e "\n${BLUE}=======================================================${NC}"
    echo -e "${CYAN}${BOLD}                 SECURITY SUITE MANAGER                ${NC}"
    echo -e "${BLUE}=======================================================${NC}"
    echo -e "  [1] Start Command Center + Telemetry Agent (Recommended)"
    echo -e "  [2] Start Standalone Server (Port 8767/8768 - SSL Mode)"
    echo -e "  [3] Start Server in Background (Hidden - Port 8765)"
    echo -e "  [4] Stop Server (Kill all ports and instances)"
    echo -e "  [5] Enable Auto-Start on Boot"
    echo -e "  [6] Disable Auto-Start on Boot"
    echo -e "  [7] Re-install Dependencies"
    echo -e "  [8] Open Dashboard in Browser"
    echo -e "  [9] Recompile Executable (PyInstaller)"
    echo -e "  [s] Sync changes to GitHub"
    echo -e "  [0] Exit"
    echo -e "${BLUE}=======================================================${NC}"
    echo -ne "  ${BOLD}Select an option:${NC} "
    read choice

    case $choice in
        1)
            clear
            echo -e "\n${BLUE}=======================================================${NC}"
            echo -e "  Starting Security Command Center..."
            echo -e "${BLUE}=======================================================${NC}"
            check_python || continue
            kill_ports
            echo -e "  [*] Starting master.py..."
            $PYTHON_EXE master.py
            read -n 1 -s -r -p "Press any key to return to menu..."
            ;;
        2)
            clear
            echo -e "\n${BLUE}=======================================================${NC}"
            echo -e "  Starting Standalone Server..."
            echo -e "${BLUE}=======================================================${NC}"
            ./start.sh
            read -n 1 -s -r -p "Press any key to return to menu..."
            ;;
        3)
            clear
            echo -e "\n${BLUE}=======================================================${NC}"
            echo -e "  Starting Server in Background..."
            echo -e "${BLUE}=======================================================${NC}"
            check_python || continue
            kill_ports
            ./run-silently.sh
            read -n 1 -s -r -p "Press any key to return to menu..."
            ;;
        4)
            clear
            ./stop-server.sh
            read -n 1 -s -r -p "Press any key to return to menu..."
            ;;
        5)
            clear
            ./setup_autostart.sh
            read -n 1 -s -r -p "Press any key to return to menu..."
            ;;
        6)
            clear
            echo -e "\n${BLUE}=======================================================${NC}"
            echo -e "  Disabling Auto-Start..."
            echo -e "${BLUE}=======================================================${NC}"
            AUTOSTART_FILE="$HOME/.config/autostart/personal-security-suite.desktop"
            if [ -f "$AUTOSTART_FILE" ]; then
                rm -f "$AUTOSTART_FILE"
                echo -e "  ${GREEN}[OK]${NC} Auto-start configuration removed."
            else
                echo -e "  [*] Auto-start entry was not active."
            fi
            read -n 1 -s -r -p "Press any key to return to menu..."
            ;;
        7)
            clear
            echo -e "\n${BLUE}=======================================================${NC}"
            echo -e "  Installing/Updating Dependencies..."
            echo -e "${BLUE}=======================================================${NC}"
            check_python || continue
            echo -e "  [*] Installing packages..."
            if ! $PYTHON_EXE -m pip install -r backend/requirements.txt --disable-pip-version-check; then
                # Retry with --break-system-packages
                $PYTHON_EXE -m pip install -r backend/requirements.txt --disable-pip-version-check --break-system-packages
            fi
            echo -e "\n  ${GREEN}[OK]${NC} Dependencies setup completed."
            read -n 1 -s -r -p "Press any key to return to menu..."
            ;;
        8)
            clear
            echo -e "\n  [*] Opening dashboard URL..."
            open_browser "http://127.0.0.1:8765"
            sleep 1
            ;;
        9)
            clear
            echo -e "\n${BLUE}=======================================================${NC}"
            echo -e "  Recompiling Security Suite Executable via PyInstaller"
            echo -e "${BLUE}=======================================================${NC}"
            check_python || continue
            echo -e "  [*] Ensuring PyInstaller is installed..."
            if ! $PYTHON_EXE -c "import PyInstaller" 2>/dev/null; then
                if ! $PYTHON_EXE -m pip install pyinstaller --break-system-packages 2>/dev/null; then
                    $PYTHON_EXE -m pip install pyinstaller 2>/dev/null
                fi
            fi
            
            echo -e "  [*] Commencing build process..."
            if $PYTHON_EXE -m PyInstaller --noconfirm --onefile --windowed --add-data "dashboard:dashboard" --add-data "backend:backend" --add-data "agent.py:." --name "SecurityCenter" master.py; then
                echo -e "\n  ${GREEN}[SUCCESS]${NC} Recompiled executable at: dist/SecurityCenter"
            else
                echo -e "\n  ${RED}[ERROR]${NC} PyInstaller compilation failed."
            fi
            read -n 1 -s -r -p "Press any key to return to menu..."
            ;;
        s|S)
            clear
            ./sync_to_github.sh
            read -n 1 -s -r -p "Press any key to return to menu..."
            ;;
        0)
            echo -e "\n  Exiting manager. Goodbye!\n"
            exit 0
            ;;
        *)
            echo -e "\n  ${RED}[!] Invalid choice. Please try again.${NC}"
            sleep 1.5
            ;;
    esac
done
