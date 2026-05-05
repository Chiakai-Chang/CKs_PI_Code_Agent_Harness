#!/usr/bin/env bash
set -e

# Restore Pi Code Agent Harness
# Usage: bash scripts/restore.sh

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PI_DIR="$HOME/.pi"
AGENT_DIR="$PI_DIR/agent"

echo "Restoring Pi harness from: $REPO_ROOT"
echo "Target: $PI_DIR"

# Create directories
mkdir -p "$AGENT_DIR/skills"
mkdir -p "$AGENT_DIR/rules"
mkdir -p "$AGENT_DIR/extensions"
mkdir -p "$AGENT_DIR/git"

# Config
cp "$REPO_ROOT/pi-config/settings.json" "$AGENT_DIR/settings.json"
cp "$REPO_ROOT/pi-config/config.json" "$AGENT_DIR/config.json"
cp "$REPO_ROOT/pi-config/git/.gitignore" "$AGENT_DIR/git/.gitignore"

# Skills
if [ -d "$REPO_ROOT/pi-skills" ]; then
  cp -r "$REPO_ROOT/pi-skills/"* "$AGENT_DIR/skills/"
fi

# Rules
if [ -d "$REPO_ROOT/pi-rules" ]; then
  cp -r "$REPO_ROOT/pi-rules/"* "$AGENT_DIR/rules/"
fi

# Extensions
if [ -d "$REPO_ROOT/pi-extensions" ]; then
  cp -r "$REPO_ROOT/pi-extensions/"* "$AGENT_DIR/extensions/"
fi

echo "Restore complete. Open Pi to verify."
