#!/bin/bash
if [ -z "$1" ]; then
    echo "Usage: ./switch-profile.sh [minimal|standard|full]"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/scripts/restore.py" --auto --profile "$1"
