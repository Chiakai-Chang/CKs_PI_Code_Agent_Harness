# Manual Restore Guide for CK's Pi Code Agent Harness

Use this only if you cannot run scripts/restore.sh, or want more control.

Prereqs:
- Node.js installed
- Git installed
- Pi installed (via npm or official method)

Assume:
- REPO_ROOT = path to this repo
- PI_DIR = ~/.pi
- AGENT_DIR = ~/.pi/agent

1. Create directories:

   - mkdir -p "$AGENT_DIR/skills"
   - mkdir -p "$AGENT_DIR/rules"
   - mkdir -p "$AGENT_DIR/extensions"
   - mkdir -p "$AGENT_DIR/git"

2. Copy config:

   - cp "$REPO_ROOT/pi-config/settings.json" "$AGENT_DIR/settings.json"
   - cp "$REPO_ROOT/pi-config/config.json"   "$AGENT_DIR/config.json"
   - cp "$REPO_ROOT/pi-config/git/.gitignore" "$AGENT_DIR/git/.gitignore"

   Then edit "$AGENT_DIR/config.json":
   - Replace any "TODO_NEW_MACHINE" prefixes with your actual HOME path.
   - Adjust external paths (e.g., everything-claude-code) as needed.

3. Copy skills:

   - cp -r "$REPO_ROOT/pi-skills/"* "$AGENT_DIR/skills/"

4. Copy rules:

   - cp -r "$REPO_ROOT/pi-rules/"* "$AGENT_DIR/rules/"

5. Copy extensions:

   - cp -r "$REPO_ROOT/pi-extensions/"* "$AGENT_DIR/extensions/"

6. Finalize:

   - pi update
   - Open Pi and confirm:
     - No skill naming conflicts
     - Extensions loaded
