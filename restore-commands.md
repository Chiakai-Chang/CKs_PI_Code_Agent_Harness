# Restore Pi Harness on a New Machine

Run these steps after:
- Installing Node.js
- Installing Git
- Installing Pi (via npm or official method)

## 1. Clone this repo

git clone git@github.com:Chiakai-Chang/CKs_PI_Code_Agent_Harness.git
cd CKs_PI_Code_Agent_Harness

## 2. Install Pi packages (recommended)

From the repo root:

- Install context-mode (global npm package, if not yet installed):
  - npm install -g context-mode

- Run Pi update to ensure latest:
  - pi update

## 3. Restore Pi config

Let:
- PI_DIR = ~/.pi
- AGENT_DIR = ~/.pi/agent

Create dirs (if missing):
- mkdir -p "$PI_DIR/agent"
- mkdir -p "$AGENT_DIR/skills"
- mkdir -p "$AGENT_DIR/rules"
- mkdir -p "$AGENT_DIR/extensions"
- mkdir -p "$AGENT_DIR/git"

Copy config (adjust paths for your OS):

- cp pi-config/settings.json "$AGENT_DIR/settings.json"
- cp pi-config/config.json "$AGENT_DIR/config.json"
- cp pi-config/git/.gitignore "$AGENT_DIR/git/.gitignore"

## 4. Restore skills

- cp -r pi-skills/* "$AGENT_DIR/skills/"

If you had external skills referenced in config.json (e.g., everything-claude-code),
you must either:
- Re-create those paths, or
- Edit config.json to remove those references.

## 5. Restore rules

- cp -r pi-rules/* "$AGENT_DIR/rules/"

## 6. Restore extensions

- cp -r pi-extensions/* "$AGENT_DIR/extensions/"

## 7. Verify

- Open Pi and confirm:
  - No skill naming conflicts
  - Extensions loaded
  - Rules visible
