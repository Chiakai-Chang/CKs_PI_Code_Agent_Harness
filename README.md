# CK's Pi Code Agent Harness

Portable Pi (code-agent harness) configuration so you can reproduce the same setup on any new machine.

Includes:
- pi-config/: settings.json, config.json, git/.gitignore
- pi-skills/: all agent skills (fixed naming conflicts)
- pi-rules/: agent rules
- pi-extensions/: extensions
- restore-commands.md: step-by-step restore guide
- scripts/restore.sh: automated restore script

Usage:
- On a new machine:
  1. Install Node, Git, and Pi.
  2. Clone this repo.
  3. Run restore-commands (or scripts/restore.sh).
