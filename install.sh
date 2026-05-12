#!/usr/bin/env bash
#
# CK's Pi Code Agent Harness - One-Click Installer (macOS / Linux)
#
# Usage:
#   ./install.sh
#   or
#   bash install.sh
#
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

clear
echo "============================================================"
echo " CK's Pi Code Agent Harness - One-Click Installer"
echo "============================================================"
echo ""
echo "This script will:"
echo "  - Check Git / Python / Node.js"
echo "  - Install Pi (AI coding assistant)"
echo "  - Apply dev skills and rules"
echo "  - Scan local LLM services (Ollama, etc.)"
echo ""
echo "It will NOT:"
echo "  - Collect personal data"
echo "  - Call external tracking APIs"
echo "  - Modify system environment variables"
echo ""
echo "Source:"
echo "  GitHub: https://github.com/Chiakai-Chang/CKs_PI_Code_Agent_Harness"
echo "  License: MIT"
echo ""
read -p "Continue? (y/N): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi
echo ""

# Admin check (best-effort)
if [[ $EUID -ne 0 ]]; then
    echo "[!] Currently not running as root/sudo."
    echo "    Some steps (e.g., npm install -g) may require it."
    echo "    If later steps fail, re-run with sudo."
    echo ""
fi

# [1/6] Initialize submodules
echo "[1/6] Initializing git submodules (ECC hooks)..."
git submodule update --init --recursive || {
    echo "[!] Submodule init failed. ECC hooks will be unavailable."
}
echo "✅ Submodule init done."
echo ""

# [2/6] Check Python
echo "[2/6] Checking Python..."
if ! command -v python3 &> /dev/null; then
  echo "[!] python3 not found. Please install Python first:"
  echo "    macOS (Homebrew): brew install python"
  echo "    Ubuntu/Debian:    sudo apt update && sudo apt install -y python3"
  echo ""
  echo "Then run again:"
  echo "    bash install.sh"
  exit 1
fi
echo "✅ Python OK."
echo ""

# [3/6] Run setup (handles Node, Pi, LLM, restore)
echo "[3/6] Running environment setup..."
python3 "$SCRIPT_DIR/scripts/setup.py" || {
    echo ""
    echo "[!] Setup failed or exited with error."
    echo ""
    echo "Possible causes:"
    echo "  - npm install -g requires sudo."
    echo "  - Network or permission issues."
    echo ""
    exit 1
}

echo ""
echo "[4/6] Environment setup complete."

# [5/6] Fallback restore if not run inside setup.py
if [ -f "$SCRIPT_DIR/scripts/restore.py" ]; then
    echo "[5/6] If restore was not run inside setup.py, run:"
    echo "    python3 scripts/restore.py"
    echo ""
fi

# [6/6] Done
echo "[6/6] Done!"
echo ""
echo " Next steps:"
echo "   1. Run: pi"
echo "   2. Confirm Skills and Extensions loaded"
echo "   3. If needed, adjust models in pi-config/settings.json or models.json"
echo ""
