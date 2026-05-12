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

# [1/2] Initialize submodules
echo "[1/2] Initializing git submodules (ECC hooks)..."
git submodule update --init --recursive || {
    echo "[!] Submodule init failed. ECC hooks will be unavailable."
}
echo "✅ Submodule init done."
echo ""

if ! command -v python3 &> /dev/null; then
  echo "[!] python3 not found. Please install Python first:"
  echo "    macOS (Homebrew): brew install python"
  echo "    Ubuntu/Debian:    sudo apt update && sudo apt install -y python3"
  echo ""
  echo "Then run again:"
  echo "    bash install.sh"
  exit 1
fi

exec python3 "$SCRIPT_DIR/scripts/setup.py"
