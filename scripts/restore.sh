#!/usr/bin/env bash
#
# CK's Pi Code Agent Harness – Restore Configuration
#
# This script only manages YOUR configuration (skills, rules, extensions, settings).
# It does NOT install or manage Pi itself.
#
# Prereqs:
# - Node.js (LTS)
# - Git
# - Pi (e.g. npm install -g @mariozechner/pi-coding-agent)
#
# Usage:
#   bash scripts/restore.sh
#
# Behavior:
# - Backs up existing ~/.pi/agent files to ~/.pi/agent.backup.<timestamp>
# - Restores core skills always
# - Optionally restores design/heavy skills if requested
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

if ! command -v pi >/dev/null 2>&1; then
  echo "[RESTORE] ⚠️  'pi' not found in PATH. Make sure you've installed Pi first."
  echo "[RESTORE]    For example: npm install -g @mariozechner/pi-coding-agent"
  echo ""
fi

mkdir -p "$AGENT_DIR/skills"
mkdir -p "$AGENT_DIR/rules"
mkdir -p "$AGENT_DIR/extensions"
mkdir -p "$AGENT_DIR/git"

if [ -d "$AGENT_DIR" ]; then
  BACKUP_DIR="${AGENT_DIR}.backup.${TIMESTAMP}"
  echo "[RESTORE] Backing up existing agent config to: $BACKUP_DIR"
  cp -r "$AGENT_DIR" "$BACKUP_DIR"
fi

if [ -t 0 ]; then
  echo ""
  echo "[RESTORE] This will overwrite:"
  echo "  - $AGENT_DIR/settings.json"
  echo "  - $AGENT_DIR/config.json"
  echo "  - $AGENT_DIR/skills/* (core + optionally design/heavy skills)"
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

# Config
echo "[RESTORE] Restoring config..."
cp "$REPO_ROOT/pi-config/settings.json" "$AGENT_DIR/settings.json"
cp "$REPO_ROOT/pi-config/config.json"   "$AGENT_DIR/config.json"
cp "$REPO_ROOT/pi-config/git/.gitignore" "$AGENT_DIR/git/.gitignore"

if grep -q "TODO_NEW_MACHINE" "$AGENT_DIR/config.json"; then
  sed -i "s|TODO_NEW_MACHINE|$HOME|g" "$AGENT_DIR/config.json"
fi

# Core skills (always)
echo "[RESTORE] Restoring core skills..."
if [ -d "$REPO_ROOT/pi-skills/core" ]; then
  rm -rf "$AGENT_DIR/skills"/*
  cp -r "$REPO_ROOT/pi-skills/core/"* "$AGENT_DIR/skills/"
fi

# Optional skills (design / heavy) – prompt
RESTORE_OPTIONAL=true
if [ -d "$REPO_ROOT/pi-skills/optional" ] && [ -t 0 ]; then
  echo ""
  echo "[RESTORE] This repo includes optional design/creative skills (heavier)."
  echo "[RESTORE] Examples: design, ui-ux-pro-max, ui-styling, slides, brand, etc."
  echo -n "[RESTORE] Restore optional skills? (Y/n): "
  read -r ANS
  if [[ "$ANS" == "n" || "$ANS" == "N" ]]; then
    RESTORE_OPTIONAL=false
  fi
fi

if [ "$RESTORE_OPTIONAL" = true ] && [ -d "$REPO_ROOT/pi-skills/optional" ]; then
  echo "[RESTORE] Restoring optional skills..."
  for dir in "$REPO_ROOT/pi-skills/optional"/*/; do
    name=$(basename "$dir")
    cp -r "$dir" "$AGENT_DIR/skills/$name"
  done
else
  echo "[RESTORE] Optional skills skipped."
fi

# Rules
echo "[RESTORE] Restoring rules..."
if [ -d "$REPO_ROOT/pi-rules" ]; then
  rm -rf "$AGENT_DIR/rules"/*
  cp -r "$REPO_ROOT/pi-rules/"* "$AGENT_DIR/rules/"
fi

# Extensions
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
