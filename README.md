# CK's Pi Code Agent Harness

Portable Pi configuration so you can reproduce the same environment on any new machine.

Includes:
- pi-config/   → settings.json, config.json, git/.gitignore
- pi-skills/   → all agent skills (naming conflicts fixed)
- pi-rules/    → agent rules
- pi-extensions/ → custom extensions
- scripts/restore.sh → automated restore script

NOT required:
- pi-mono or badlogic/pi-mono
- Any manual build of the coding-agent package

Restore on a new machine (recommended):

1. Install:
   - Node.js (LTS)
   - Git
   - Pi:
     - npm install -g @mariozechner/pi-coding-agent

2. Clone this repo:
   - git clone git@github.com:Chiakai-Chang/CKs_PI_Code_Agent_Harness.git
   - cd CKs_PI_Code_Agent_Harness

3. Run restore:
   - bash scripts/restore.sh

4. Finalize:
   - pi update
   - Open Pi; confirm:
     - Skills are loaded without conflicts
     - Extensions are active
   - If you use external paths (e.g., everything-claude-code),
     open ~/.pi/agent/config.json and adjust to your local paths.

Manual restore (if needed):
- See restore-commands.md
