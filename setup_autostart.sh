#!/usr/bin/env bash
# ==============================================================================
# Personal Security Suite — Auto-Start Setup Script (Linux)
# ==============================================================================

# ANSI Color Codes
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -ne "\033]0;Setup Auto-Start — Security Suite\007"

echo -e "\n${BLUE}=======================================================${NC}"
echo -e "${CYAN}${BOLD}       Setting up Security Suite Auto-Start            ${NC}"
echo -e "${BLUE}=======================================================${NC}\n"

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
AUTOSTART_DIR="$HOME/.config/autostart"

# Create autostart directory if it doesn't exist
mkdir -p "$AUTOSTART_DIR"

# Write desktop entry file
cat << EOF > "$AUTOSTART_DIR/personal-security-suite.desktop"
[Desktop Entry]
Type=Application
Exec=$SCRIPT_DIR/run-silently.sh
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Personal Security Suite
Comment=Launches Personal Security Suite silently on user logon
EOF

chmod +x "$AUTOSTART_DIR/personal-security-suite.desktop"

echo -e "  ${GREEN}[OK]${NC} Auto-start configured! Security Suite will launch silently when you log in."
echo -e "  (Created: $AUTOSTART_DIR/personal-security-suite.desktop)"
echo -e "\n  To disable auto-start, run: ${YELLOW}rm -f \"$AUTOSTART_DIR/personal-security-suite.desktop\"${NC}\n"
sleep 2
