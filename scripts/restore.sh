#!/usr/bin/env bash
#
# CK's Pi Code Agent Harness – Restore Configuration (Delegates to restore.py)
#
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/restore.py" "$@"
