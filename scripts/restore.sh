#!/usr/bin/env bash
#
# CK's Pi Code Agent Harness – Restore Configuration
#
# This script only manages YOUR configuration (skills, rules, extensions, settings).
# It does NOT install or manage Pi itself.
#
# Prereqs (user must install separately):
# - Node.js (LTS)
# - Git
# - Pi (e.g. npm install -g @mariozechner/pi-coding-agent)
#
# Usage:
#   bash scripts/restore.sh
#
# Behavior:
# - Backs up existing ~/.pi/agent files to ~/.pi/agent.backup.<timestamp>
# - Copies config from this repo into ~/.pi/agent
# - Safe to run again when you want to sync config updates
#
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PI_DIR="$HOME/.pi"
AGENT_DIR="$PI_DIR/agent"
TIMESTAMP="$(date +%Y%m%dT%H%M%S)"

echo "=== CK's Pi Code Agent Harness – Restore ==="
echo "Repo root: $REPO_ROOT"
echo "Pi dir:    $PI_DIR"
echo ""

# If Pi is not installed yet, warn but continue
if ! command -v pi >/dev/null 2>&1; then
  echo "⚠️  'pi' not found in PATH. Make sure you've installed Pi first."
  echo "   For example: npm install -g @mariozechner/pi-coding-agent"
  echo ""
fi

# 1. Ensure directories
mkdir -p "$AGENT_DIR/skills"
mkdir -p "$AGENT_DIR/rules"
mkdir -p "$AGENT_DIR/extensions"
mkdir -p "$AGENT_DIR/git"

# 2. Backup existing agent folder (if present)
if [ -d "$AGENT_DIR" ]; then
  BACKUP_DIR="${AGENT_DIR}.backup.${TIMESTAMP}"
  echo "Backing up existing agent config to: $BACKUP_DIR"
  cp -r "$AGENT_DIR" "$BACKUP_DIR"
fi

# 3. Restore config
echo "Restoring config..."
cp "$REPO_ROOT/pi-config/settings.json" "$AGENT_DIR/settings.json"
cp "$REPO_ROOT/pi-config/config.json"   "$AGENT_DIR/config.json"
cp "$REPO_ROOT/pi-config/git/.gitignore" "$AGENT_DIR/git/.gitignore"

# 4. Normalize TODO_NEW_MACHINE placeholders in config.json
echo "Fixing paths in config.json..."
if grep -q "TODO_NEW_MACHINE" "$AGENT_DIR/config.json"; then
  sed -i "s|TODO_NEW_MACHINE|$HOME|g" "$AGENT_DIR/config.json"
fi

# 5. Restore skills
echo "Restoring skills..."
if [ -d "$REPO_ROOT/pi-skills" ]; then
  rm -rf "$AGENT_DIR/skills"/*
  cp -r "$REPO_ROOT/pi-skills/"* "$AGENT_DIR/skills/"
fi

# 6. Restore rules
echo "Restoring rules..."
if [ -d "$REPO_ROOT/pi-rules" ]; then
  rm -rf "$AGENT_DIR/rules"/*
  cp -r "$REPO_ROOT/pi-rules/"* "$AGENT_DIR/rules/"
fi

# 7. Restore extensions
echo "Restoring extensions..."
if [ -d "$REPO_ROOT/pi-extensions" ]; then
  rm -rf "$AGENT_DIR/extensions"/*
  cp -r "$REPO_ROOT/pi-extensions/"* "$AGENT_DIR/extensions/"
fi

echo ""
echo "✅ Restore complete."
echo ""
echo "📌 Next steps:"
echo "  1) Ensure Pi is installed:"
echo "     - npm install -g @mariozechner/pi-coding-agent"
echo "  2) Update Pi to latest:"
echo "     - pi update"
echo "  3) Open Pi and confirm:"
echo "     - Skills loaded without conflicts"
echo "     - Extensions loaded"
echo ""
echo "📌 If you use external paths (e.g., everything-claude-code),"
echo "   edit ~/.pi/agent/config.json and adjust them for your machine."
echo ""
echo "🔄 To apply future config updates from this repo:"
echo "   - cd to this repo"
echo "   - git pull"
echo "   - bash scripts/restore.sh"
