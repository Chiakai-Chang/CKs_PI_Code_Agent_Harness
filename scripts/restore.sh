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

echo "[RESTORE] CK's Pi Code Agent Harness – Restore Configuration"
echo "[RESTORE] Repo root: $REPO_ROOT"
echo "[RESTORE] Pi dir:    $PI_DIR"
echo "[RESTORE] Agent dir: $AGENT_DIR"
echo ""

# If Pi is not installed yet, warn but continue
if ! command -v pi >/dev/null 2>&1; then
  echo "[RESTORE] ⚠️  'pi' not found in PATH. Make sure you've installed Pi first."
  echo "[RESTORE]    For example: npm install -g @mariozechner/pi-coding-agent"
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
  echo "[RESTORE] Backing up existing agent config to: $BACKUP_DIR"
  cp -r "$AGENT_DIR" "$BACKUP_DIR"
fi

# 3. Confirm overwrite (unless piped/non-interactive)
if [ -t 0 ]; then
  echo ""
  echo "[RESTORE] This will overwrite:"
  echo "  - $AGENT_DIR/settings.json"
  echo "  - $AGENT_DIR/config.json"
  echo "  - $AGENT_DIR/skills/*"
  echo "  - $AGENT_DIR/rules/*"
  echo "  - $AGENT_DIR/extensions/*"
  echo "  - $AGENT_DIR/git/.gitignore"
  echo "[RESTORE] A backup has been saved to: ${AGENT_DIR}.backup.${TIMESTAMP}"
  echo ""
  echo -n "[RESTORE] Continue? (y/N): "
  read -r CONFIRM
  case "$CONFIRM" in
    [yY]*) ;;
    *)
      echo "[RESTORE] Aborted by user."
      exit 0
      ;;
  esac
fi

# 4. Restore config
echo "[RESTORE] Restoring config..."
cp "$REPO_ROOT/pi-config/settings.json" "$AGENT_DIR/settings.json"
cp "$REPO_ROOT/pi-config/config.json"   "$AGENT_DIR/config.json"
cp "$REPO_ROOT/pi-config/git/.gitignore" "$AGENT_DIR/git/.gitignore"

# 5. Normalize TODO_NEW_MACHINE placeholders in config.json
echo "[RESTORE] Fixing paths in config.json..."
if grep -q "TODO_NEW_MACHINE" "$AGENT_DIR/config.json"; then
  sed -i "s|TODO_NEW_MACHINE|$HOME|g" "$AGENT_DIR/config.json"
fi

# 6. Restore skills
echo "[RESTORE] Restoring skills..."
if [ -d "$REPO_ROOT/pi-skills" ]; then
  rm -rf "$AGENT_DIR/skills"/*
  cp -r "$REPO_ROOT/pi-skills/"* "$AGENT_DIR/skills/"
fi

# 7. Restore rules
echo "[RESTORE] Restoring rules..."
if [ -d "$REPO_ROOT/pi-rules" ]; then
  rm -rf "$AGENT_DIR/rules"/*
  cp -r "$REPO_ROOT/pi-rules/"* "$AGENT_DIR/rules/"
fi

# 8. Restore extensions
echo "[RESTORE] Restoring extensions..."
if [ -d "$REPO_ROOT/pi-extensions" ]; then
  rm -rf "$AGENT_DIR/extensions"/*
  cp -r "$REPO_ROOT/pi-extensions/"* "$AGENT_DIR/extensions/"
fi

echo ""
echo "[RESTORE] ✅ Restore complete."
echo ""
echo "[RESTORE] 📌 Next steps:"
echo "  1) Ensure Pi is installed:"
echo "     - npm install -g @mariozechner/pi-coding-agent"
echo "  2) Update Pi to latest:"
echo "     - pi update"
echo "  3) Open Pi and confirm:"
echo "     - Skills loaded without conflicts"
echo "     - Extensions loaded"
echo ""
echo "[RESTORE] 📌 If you use external paths (e.g., everything-claude-code),"
echo "   edit ~/.pi/agent/config.json and adjust them for your machine."
echo ""
echo "[RESTORE] 🔄 To apply future config updates from this repo:"
echo "   - cd to this repo"
echo "   - git pull"
echo "   - bash scripts/restore.sh"
echo ""
echo "[RESTORE] If you encounter issues, copy the output above when asking for help."
