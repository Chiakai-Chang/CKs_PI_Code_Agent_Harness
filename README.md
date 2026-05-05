# CK's Pi Code Agent Harness

Portable Pi (code-agent harness) configuration so you can reproduce the same setup on any new machine.

Includes:
- pi-config/: settings.json, config.json, git/.gitignore
- pi-skills/: all agent skills (fixed naming conflicts)
- pi-rules/: agent rules
- pi-extensions/: extensions
- restore-commands.md: step-by-step restore guide
- scripts/restore.sh: automated restore script

What was fixed:
- 6 skill naming conflicts resolved:
  - ckm:banner-design -> banner-design
  - ckm:brand -> brand
  - ckm:design -> design
  - ckm:design-system -> design-system
  - ckm:slides -> slides
  - ckm:ui-styling -> ui-styling
  Now all names match their folder and use only allowed characters.

Usage (on a new machine):
1. Install:
   - Node.js
   - Git
   - Pi (via npm or official installer)
2. Clone this repo:
   - git clone git@github.com:Chiakai-Chang/CKs_PI_Code_Agent_Harness.git
   - cd CKs_PI_Code_Agent_Harness
3. Run:
   - pi update
4. Restore:
   - Read restore-commands.md
   - Or run: bash scripts/restore.sh
5. Adjust local paths:
   - In pi-config/config.json:
     - Update paths that reference your local disks (e.g., D:/MyProject/...) to match your new machine.
