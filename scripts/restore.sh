#!/usr/bin/env bash
#
# Restore CK's Pi Code Agent Harness on a new machine.
#
# Prereqs:
# - Node.js installed
# - Git installed
# - Pi installed (e.g. npm install -g @mariozechner/pi-coding-agent)
#
# Usage:
#   bash scripts/restore.sh
#
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PI_DIR="$HOME/.pi"
AGENT_DIR="$PI_DIR/agent"

echo "=== CK's Pi Code Agent Harness - Restore ==="
echo "Repo root: $REPO_ROOT"
echo "Pi dir:    $PI_DIR"
echo ""

# 1. Ensure directory structure
mkdir -p "$AGENT_DIR/skills"
mkdir -p "$AGENT_DIR/rules"
mkdir -p "$AGENT_DIR/extensions"
mkdir -p "$AGENT_DIR/git"

# 2. Copy config (excluding auth)
echo "Restoring config..."
cp "$REPO_ROOT/pi-config/settings.json" "$AGENT_DIR/settings.json"
cp "$REPO_ROOT/pi-config/config.json"   "$AGENT_DIR/config.json"
cp "$REPO_ROOT/pi-config/git/.gitignore" "$AGENT_DIR/git/.gitignore"

# 3. Replace TODO_NEW_MACHINE placeholders in config.json with HOME-based defaults
echo "Fixing paths in config.json..."
if grep -q "TODO_NEW_MACHINE" "$AGENT_DIR/config.json"; then
  sed -i "s|TODO_NEW_MACHINE|$HOME|g" "$AGENT_DIR/config.json"
fi

# 4. Copy skills
echo "Restoring skills..."
if [ -d "$REPO_ROOT/pi-skills" ]; then
  cp -r "$REPO_ROOT/pi-skills/"* "$AGENT_DIR/skills/"
fi

# 5. Copy rules
echo "Restoring rules..."
if [ -d "$REPO_ROOT/pi-rules" ]; then
  cp -r "$REPO_ROOT/pi-rules/"* "$AGENT_DIR/rules/"
fi

# 6. Copy extensions
echo "Restoring extensions..."
if [ -d "$REPO_ROOT/pi-extensions" ]; then
  cp -r "$REPO_ROOT/pi-extensions/"* "$AGENT_DIR/extensions/"
fi

echo ""
echo "Restore complete."
echo ""
echo "Next steps:"
echo "  1) Open Pi and run: pi update"
echo "  2) If you use everything-claude-code or custom skills,"
echo "     edit ~/.pi/agent/config.json and update paths."
echo "  3) Open Pi and confirm no skill conflicts."
