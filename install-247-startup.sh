#!/usr/bin/env bash
# ==============================================================================
# Personal Security Suite — 24/7 Startup Installer (Linux)
# ==============================================================================

# Get current script directory and invoke setup_autostart.sh
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
exec "$SCRIPT_DIR/setup_autostart.sh"
