#!/usr/bin/env bash
#
# CK's Pi Code Agent Harness - Updater
# License: MIT (open-source)
#
set -e

if ! command -v python3 &> /dev/null; then
    echo "[!] python3 not found. Please install Python first."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/scripts/setup.py" --mode update
