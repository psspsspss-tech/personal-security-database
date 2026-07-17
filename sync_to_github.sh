#!/usr/bin/env bash
# ==============================================================================
# Personal Security Suite — GitHub Sync Script (Linux)
# ==============================================================================

# ANSI Color Codes
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "\n${BLUE}=======================================================${NC}"
echo -e "${CYAN}${BOLD}       Syncing Security Command Center to GitHub       ${NC}"
echo -e "${BLUE}=======================================================${NC}\n"

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo -e "${RED}[ERROR] Git is not installed or not in your PATH.${NC}"
    echo -e "Please install Git via your package manager (e.g., sudo apt install git)."
    exit 1
fi

COMMIT_MSG="Auto-sync: $(date +'%Y-%m-%d %H:%M:%S')"

echo -e "  [1/3] Adding changes to Git..."
git add .

echo -e "  [2/3] Committing changes..."
git commit -m "$COMMIT_MSG"

echo -e "  [3/3] Pushing to GitHub..."
if git push origin main; then
    echo -e "\n${GREEN}[SUCCESS] All changes pushed to GitHub!${NC}\n"
else
    echo -e "\n${RED}[ERROR] Failed to push. Make sure your GitHub remote and authentication are configured.${NC}\n"
fi
