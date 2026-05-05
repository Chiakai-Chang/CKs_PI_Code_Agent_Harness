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
