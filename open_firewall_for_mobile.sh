#!/usr/bin/env bash
# ==============================================================================
# Personal Security Suite — Open Firewall for Mobile Access (Linux)
# ==============================================================================

# ANSI Color Codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -ne "\033]0;Security Suite — Open Firewall for Mobile Access\007"

echo -e "\n${BLUE}=======================================================${NC}"
echo -e "${CYAN}${BOLD}     Open Firewall for Mobile/Network Access           ${NC}"
echo -e "${BLUE}=======================================================${NC}\n"
echo -e "  This opens firewall ports 8765 and 8767 so your other devices"
echo -e "  (e.g., iPhone, Android, local laptop) can access the dashboard.\n"

# Get Local IP
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP=$(ip route get 1.0.0.0 2>/dev/null | awk '{print $7}')
fi
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP="127.0.0.1"
fi

if [ "$EUID" -ne 0 ]; then
    echo -e "  ${YELLOW}[*] Administrator (root) privileges needed to apply firewall rules.${NC}"
    echo -e "      We will prompt you for sudo credentials if needed.\n"
fi

# Detect firewall managers
if command -v ufw &> /dev/null; then
    echo -e "  [*] UFW (Uncomplicated Firewall) detected."
    echo -e "  [*] Running: sudo ufw allow 8765/tcp && sudo ufw allow 8767/tcp"
    if sudo ufw allow 8765/tcp && sudo ufw allow 8767/tcp; then
        echo -e "  ${GREEN}[OK]${NC} Firewall rules added successfully."
    else
        echo -e "  ${RED}[FAIL]${NC} Failed to add UFW rules."
    fi
elif command -v firewall-cmd &> /dev/null; then
    echo -e "  [*] firewalld detected."
    echo -e "  [*] Running: sudo firewall-cmd --add-port=8765/tcp --permanent ..."
    if sudo firewall-cmd --add-port=8765/tcp --add-port=8767/tcp --permanent && sudo firewall-cmd --reload; then
        echo -e "  ${GREEN}[OK]${NC} Firewall rules added and reloaded successfully."
    else
        echo -e "  ${RED}[FAIL]${NC} Failed to add firewalld rules."
    fi
elif command -v iptables &> /dev/null; then
    echo -e "  [*] iptables detected."
    echo -e "  [*] Running: sudo iptables -A INPUT -p tcp --dport 8765 -j ACCEPT ..."
    if sudo iptables -A INPUT -p tcp --dport 8765 -j ACCEPT && sudo iptables -A INPUT -p tcp --dport 8767 -j ACCEPT; then
        echo -e "  ${GREEN}[OK]${NC} iptables rules added successfully."
    else
        echo -e "  ${RED}[FAIL]${NC} Failed to add iptables rules."
    fi
else
    echo -e "  ${YELLOW}[WARN]${NC} No standard firewall manager (ufw, firewalld, iptables) was auto-detected."
    echo -e "         Please manually open ports ${CYAN}8765${NC} and ${CYAN}8767${NC} on your system's firewall."
fi

echo -e "\n${BLUE}=======================================================${NC}"
echo -e "  Your Mobile Dashboard URL:  ${GREEN}http://${LOCAL_IP}:8765${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo -e "  On iPhone/Android web browser:"
echo -e "    1. Type the URL above"
echo -e "    2. Tap Share / Menu -> Add to Home Screen"
echo -e "${BLUE}=======================================================${NC}\n"
