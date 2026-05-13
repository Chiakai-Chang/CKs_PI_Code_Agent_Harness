#!/usr/bin/env bash
#
# CK's Pi Code Agent Harness - Bootstrapper
#
set -e

# --- 1. Find Python ---
if ! command -v python3 &> /dev/null; then
    echo "[!] python3 not found. Please install Python first."
    exit 1
fi

# --- 2. Self-Elevation (Optional for Unix, usually handled by sudo inside) ---
# We let setup.py handle specific sudo needs or use it here if preferred.

# --- 3. Launch the Brain (setup.py) ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/scripts/setup.py"
