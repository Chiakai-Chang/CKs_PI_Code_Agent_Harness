#!/usr/bin/env bash
#
# CK's Pi Code Agent Harness - Bootstrapper
# License: MIT (open-source)
#
set -e

# --- 1. Find Python ---
if ! command -v python3 &> /dev/null; then
    echo "[!] python3 not found. Please install Python first."
    exit 1
fi

# --- 2. Confirmation Prompt ---
read -p "Continue? (Y/n): " confirm
if [[ "$confirm" =~ ^[nN]$ ]]; then
    echo "Aborted."
    exit 0
fi

# --- 3. Launch the Brain (setup.py) ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/scripts/setup.py"
