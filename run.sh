#!/usr/bin/env bash
# ==============================================================================
# Personal Security Suite — Unified Controller (Linux)
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
echo -ne "\033]0;Personal Security Suite Controller\007"

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

# Verification helpers
check_python() {
    if [ -z "$PYTHON_EXE" ]; then
        echo -e "\n  ${RED}[ERROR] Python is not installed or not in PATH.${NC}"
        echo -e "  Please install Python 3.9+ from your distribution package manager."
        return 1
    fi
    return 0
}

# Safely kill old processes on specific ports
kill_port() {
    local port=$1
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
}

# Open dashboard URL in default browser
open_browser() {
    local url=$1
    if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
        if command -v xdg-open &> /dev/null; then
            xdg-open "$url" >/dev/null 2>&1 &
        elif command -v sensible-browser &> /dev/null; then
            sensible-browser "$url" >/dev/null 2>&1 &
        fi
    fi
}

# Get network IP address
get_local_ip() {
    local ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [ -z "$ip" ]; then
        ip=$(ip route get 1.0.0.0 2>/dev/null | awk '{print $7}')
    fi
    if [ -z "$ip" ]; then
        ip="127.0.0.1"
    fi
    echo "$ip"
}

# ==============================================================================
# SUB-COMMANDS (Corresponding to individual .bat files)
# ==============================================================================

# 1. start.bat -> start_server
start_server() {
    echo -e "\n${BLUE}=======================================================${NC}"
    echo -e "${CYAN}${BOLD}          Personal Security Command Center             ${NC}"
    echo -e "${BLUE}=======================================================${NC}\n"
    
    kill_port 8767
    kill_port 8768
    sleep 1

    check_python || exit 1
    echo -e "  ${GREEN}[OK]${NC} Python found ($($PYTHON_EXE --version | head -n 1))."

    echo -e "  [*] Verifying Python dependencies..."
    install_deps_silent

    LOCAL_IP=$(get_local_ip)
    echo -e "\n${BLUE}=======================================================${NC}"
    echo -e "  ${BOLD}Dashboard URLs:${NC}"
    echo -e "    This PC  :  ${GREEN}https://127.0.0.1:8767${NC}"
    echo -e "    Network  :  ${GREEN}https://${LOCAL_IP}:8767${NC}"
    echo -e "${BLUE}=======================================================${NC}"
    echo -e "  Scan the QR code in the dashboard to open on mobile"
    echo -e "${BLUE}=======================================================${NC}\n"
    echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop the server.\n"

    cd "$SCRIPT_DIR/backend"
    sleep 2
    open_browser "https://127.0.0.1:8767"
    $PYTHON_EXE server.py
}

# 2. Stop-Server.bat -> stop_server
stop_server() {
    echo -e "\n${BLUE}=======================================================${NC}"
    echo -e "${RED}             Stopping Security Suite...                ${NC}"
    echo -e "${BLUE}=======================================================${NC}\n"

    # Disable autostart file if present
    local autostart_file="$HOME/.config/autostart/personal-security-suite.desktop"
    if [ -f "$autostart_file" ]; then
        echo -e "  [*] Disabling auto-start..."
        rm -f "$autostart_file"
    fi

    echo -e "  [*] Terminating server loops and python processes..."
    pkill -f "run.sh loop" >/dev/null 2>&1
    pkill -f "python.*master.py" >/dev/null 2>&1
    pkill -f "python.*server.py" >/dev/null 2>&1
    pkill -f "python.*agent.py" >/dev/null 2>&1

    for port in 8765 8766 8767 8768; do
        kill_port $port
    done

    echo -e "\n${BLUE}=======================================================${NC}"
    echo -e "  ${GREEN}[OK]${NC} Security Suite fully stopped."
    echo -e "${BLUE}=======================================================${NC}\n"
}

# 3. Server-Loop.bat -> server_loop
server_loop() {
    check_python || exit 1
    while true; do
        echo "  [*] Launching master.py..."
        $PYTHON_EXE master.py
        echo ""
        echo "  [!] Server stopped. Restarting in 5 seconds..."
        sleep 5
    done
}

# 4. Run-Silently.bat -> run_silently
run_silently() {
    nohup "$SCRIPT_DIR/run.sh" loop > /dev/null 2>&1 &
    echo -e "\n  ${GREEN}[OK]${NC} Security Suite is running silently in the background."
    echo -e "  (To stop it, run: ./run.sh stop)\n"
    sleep 3
}

# 5. setup_autostart.bat / Install-247-Startup.bat -> setup_autostart
setup_autostart() {
    echo -e "\n${BLUE}=======================================================${NC}"
    echo -e "${CYAN}${BOLD}       Setting up Security Suite Auto-Start            ${NC}"
    echo -e "${BLUE}=======================================================${NC}\n"

    local autostart_dir="$HOME/.config/autostart"
    mkdir -p "$autostart_dir"

    cat << EOF > "$autostart_dir/personal-security-suite.desktop"
[Desktop Entry]
Type=Application
Exec=$SCRIPT_DIR/run.sh silent
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Personal Security Suite
Comment=Launches Personal Security Suite silently on user logon
EOF

    chmod +x "$autostart_dir/personal-security-suite.desktop"
    echo -e "  ${GREEN}[OK]${NC} Auto-start configured to launch silently on logon."
    echo -e "\n  To disable auto-start, run: ${YELLOW}./run.sh stop${NC}\n"
    sleep 2
}

# 6. open_firewall_for_mobile.bat -> open_firewall
open_firewall() {
    echo -e "\n${BLUE}=======================================================${NC}"
    echo -e "${CYAN}${BOLD}     Open Firewall for Mobile/Network Access           ${NC}"
    echo -e "${BLUE}=======================================================${NC}\n"

    if [ "$EUID" -ne 0 ]; then
        echo -e "  ${YELLOW}[*] Root privileges needed to apply firewall rules. Triggering sudo...${NC}"
    fi

    if command -v ufw &> /dev/null; then
        sudo ufw allow 8765/tcp && sudo ufw allow 8767/tcp
    elif command -v firewall-cmd &> /dev/null; then
        sudo firewall-cmd --add-port=8765/tcp --add-port=8767/tcp --permanent && sudo firewall-cmd --reload
    elif command -v iptables &> /dev/null; then
        sudo iptables -A INPUT -p tcp --dport 8765 -j ACCEPT && sudo iptables -A INPUT -p tcp --dport 8767 -j ACCEPT
    else
        echo -e "  ${YELLOW}[WARN]${NC} No firewall manager detected. Open ports 8765 and 8767 manually."
    fi

    LOCAL_IP=$(get_local_ip)
    echo -e "\n  Mobile Dashboard URL: ${GREEN}http://${LOCAL_IP}:8765${NC}\n"
}

# 7. sync_to_github.bat -> sync_github
sync_github() {
    echo -e "\n${BLUE}=======================================================${NC}"
    echo -e "${CYAN}${BOLD}       Syncing Security Command Center to GitHub       ${NC}"
    echo -e "${BLUE}=======================================================${NC}\n"

    if ! command -v git &> /dev/null; then
        echo -e "${RED}[ERROR] Git is not installed.${NC}"
        return 1
    fi

    git add .
    git commit -m "Auto-sync: $(date +'%Y-%m-%d %H:%M:%S')"
    git push origin main
}

# 8. manager.bat -> interactive_menu
interactive_menu() {
    while true; do
        clear
        echo -e "\n${BLUE}=======================================================${NC}"
        echo -e "${CYAN}${BOLD}             SECURITY SUITE - UNIFIED CONTROLLER       ${NC}"
        echo -e "${BLUE}=======================================================${NC}"
        echo -e "  [1] Start Command Center + Telemetry Agent (Recommended)"
        echo -e "  [2] Start Standalone Server (Port 8767/8768 - SSL Mode)"
        echo -e "  [3] Start Server in Background (Hidden)"
        echo -e "  [4] Stop All Server Instances / Processes"
        echo -e "  [5] Enable Auto-Start on Boot"
        echo -e "  [6] Open Dashboard in Browser"
        echo -e "  [7] Open Firewall for Mobile Access"
        echo -e "  [8] Re-install Dependencies"
        echo -e "  [9] Recompile Executable (PyInstaller)"
        echo -e "  [s] Sync Changes to GitHub"
        echo -e "  [0] Exit"
        echo -e "${BLUE}=======================================================${NC}"
        echo -ne "  ${BOLD}Select an option:${NC} "
        read choice

        case $choice in
            1)
                clear
                check_python || continue
                kill_port 8765
                kill_port 8767
                kill_port 8768
                $PYTHON_EXE master.py
                read -n 1 -s -r -p "Press any key to return..."
                ;;
            2)
                clear
                start_server
                read -n 1 -s -r -p "Press any key to return..."
                ;;
            3)
                clear
                check_python || continue
                kill_port 8765
                kill_port 8767
                kill_port 8768
                run_silently
                read -n 1 -s -r -p "Press any key to return..."
                ;;
            4)
                clear
                stop_server
                read -n 1 -s -r -p "Press any key to return..."
                ;;
            5)
                clear
                setup_autostart
                read -n 1 -s -r -p "Press any key to return..."
                ;;
            6)
                open_browser "http://127.0.0.1:8765"
                ;;
            7)
                clear
                open_firewall
                read -n 1 -s -r -p "Press any key to return..."
                ;;
            8)
                clear
                echo -e "\n  [*] Installing dependencies..."
                install_deps
                read -n 1 -s -r -p "Press any key to return..."
                ;;
            9)
                clear
                check_python || continue
                # Ensure PyInstaller
                if ! $PYTHON_EXE -c "import PyInstaller" 2>/dev/null; then
                    $PYTHON_EXE -m pip install pyinstaller --break-system-packages 2>/dev/null || $PYTHON_EXE -m pip install pyinstaller 2>/dev/null
                fi
                $PYTHON_EXE -m PyInstaller --noconfirm --onefile --windowed --add-data "dashboard:dashboard" --add-data "backend:backend" --add-data "agent.py:." --name "SecurityCenter" master.py
                read -n 1 -s -r -p "Press any key to return..."
                ;;
            s|S)
                clear
                sync_github
                read -n 1 -s -r -p "Press any key to return..."
                ;;
            0)
                exit 0
                ;;
        esac
    done
}

# Helper dependency installers
install_deps_silent() {
    if ! $PYTHON_EXE -m pip install -r "$SCRIPT_DIR/backend/requirements.txt" --quiet --disable-pip-version-check 2>/dev/null; then
        $PYTHON_EXE -m pip install -r "$SCRIPT_DIR/backend/requirements.txt" --quiet --disable-pip-version-check --break-system-packages 2>/dev/null
    fi
}

install_deps() {
    if ! $PYTHON_EXE -m pip install -r "$SCRIPT_DIR/backend/requirements.txt" --disable-pip-version-check; then
        $PYTHON_EXE -m pip install -r "$SCRIPT_DIR/backend/requirements.txt" --disable-pip-version-check --break-system-packages
    fi
}

# ==============================================================================
# ENTRY POINT
# ==============================================================================

case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    loop)
        server_loop
        ;;
    silent)
        run_silently
        ;;
    autostart)
        setup_autostart
        ;;
    firewall)
        open_firewall
        ;;
    sync)
        sync_github
        ;;
    menu|manager)
        interactive_menu
        ;;
    *)
        # Default behavior: If no argument or double click/run, start the server directly!
        start_server
        ;;
esac
