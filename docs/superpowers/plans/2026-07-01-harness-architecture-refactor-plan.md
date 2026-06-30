# CK's Pi Harness Architecture Refactor Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor CK's Pi Harness to use `settings.json` for mapping external submodules, fix `package.json` warning paths, add interactive skill profile selection, and delegate shell scripts.

**Architecture:** We will replace the deprecated `config.json` logic with dynamic path injection inside the global `settings.json`. Submodule skill selection will be managed via `minimal`, `standard`, and `full` profiles selected at installation.

**Tech Stack:** Python 3, Node.js, JSON, Shell Scripting.

---

### Task 1: Refactoring package.json

**Files:**
- Modify: [package.json](file:///D:/Myproject/CKs_PI_Code_Agent_Harness/package.json)

- [ ] **Step 1: Edit package.json to remove non-existent local skill paths**
Replace the `pi.skills` block to exclude path mappings that do not exist locally (they will be registered via `settings.json` dynamically).
Modify `package.json` to only list:
```json
    "skills": [
      "pi-skills/core",
      "pi-skills/chrome-cdp",
      "pi-skills/dev-browser",
      "pi-skills/optional"
    ]
```

- [ ] **Step 2: Commit changes**
```bash
git add package.json
git commit -m "refactor: remove invalid local skill paths from package.json"
```

---

### Task 2: Refactoring pi-config/settings.json.example

**Files:**
- Modify: [pi-config/settings.json.example](file:///D:/Myproject/CKs_PI_Code_Agent_Harness/pi-config/settings.json.example)
- Modify: [pi-config/settings.json](file:///D:/Myproject/CKs_PI_Code_Agent_Harness/pi-config/settings.json)

- [ ] **Step 1: Add empty skills and extensions placeholder arrays to settings.json.example**
Ensure the example file contains the required placeholder keys so they are recognized by the settings manager.
```json
{
  "packages": [
    "npm:context-mode",
    "npm:@tintinweb/pi-tasks"
  ],
  "skills": [],
  "extensions": [],
  "shellPath": "",
  "lastChangelogVersion": "0.73.0",
  "defaultProvider": "ollama",
  "defaultModel": "llama3.2",
  "apiBase": "http://localhost:11434"
}
```

- [ ] **Step 2: Add placeholder arrays to existing settings.json**
Add `"skills": []` and `"extensions": []` to [settings.json](file:///D:/Myproject/CKs_PI_Code_Agent_Harness/pi-config/settings.json).

- [ ] **Step 3: Commit settings config changes**
```bash
git add pi-config/settings.json.example pi-config/settings.json
git commit -m "config: add skills and extensions placeholders to settings.json template"
```

---

### Task 3: Refactoring scripts/restore.py

**Files:**
- Modify: [scripts/restore.py](file:///D:/Myproject/CKs_PI_Code_Agent_Harness/scripts/restore.py)

- [ ] **Step 1: Implement Deep Merge and dynamic path injection**
Edit `restore.py` to:
1. Parse `--profile` command-line argument (`minimal`, `standard`, `full`).
2. Implement `deep_merge(target, source)` to merge `settings.json` without wiping user values.
3. Dynamically resolve absolute paths of submodules for the selected profile.
4. Inject resolved paths into `skills` and `extensions` of the user's `settings.json`.
5. Remove `config.json` creation and copy logic.
6. Delete `~/.pi/agent/config.json` if it exists.

The profile paths should be mapped as defined in the Design Spec.

- [ ] **Step 2: Commit scripts/restore.py refactoring**
```bash
git add scripts/restore.py
git commit -m "refactor: migrate submodule path injection to settings.json in restore.py"
```

---

### Task 4: Refactoring scripts/setup.py

**Files:**
- Modify: [scripts/setup.py](file:///D:/Myproject/CKs_PI_Code_Agent_Harness/scripts/setup.py)

- [ ] **Step 1: Add interactive Profile Selection prompt**
Edit `setup.py` to prompt the user to choose a Skill Profile:
1. `minimal` (Core + Caveman)
2. `standard` (Default - Core + Superpowers + Karpathy + Planning + BDD)
3. `full` (All skills)
Pass this choice as `--profile` argument to `restore.py`.

- [ ] **Step 2: Commit scripts/setup.py updates**
```bash
git add scripts/setup.py
git commit -m "feat: add interactive skill profile selection to setup.py"
```

---

### Task 5: Refactoring scripts/restore.sh

**Files:**
- Modify: [scripts/restore.sh](file:///D:/Myproject/CKs_PI_Code_Agent_Harness/scripts/restore.sh)

- [ ] **Step 1: Delegate bash restore script execution to python restore script**
Edit `restore.sh` to forward all arguments to `restore.py`.
```bash
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/restore.py" "$@"
```

- [ ] **Step 2: Commit scripts/restore.sh cleanup**
```bash
git add scripts/restore.sh
git commit -m "refactor: delegate restore.sh execution to restore.py"
```

---

### Task 6: Verification

**Files:**
- None (Verification step)

- [ ] **Step 1: Run the installer script**
Run `python scripts/setup.py`, select the default `standard` profile and choose a model.

- [ ] **Step 2: Verify settings.json output**
Check if `~/.pi/agent/settings.json` contains the resolved absolute paths to superpowers, karpathy, planning-with-files, etc. in `skills` and `extensions`.
Check that `~/.pi/agent/config.json` is deleted.

- [ ] **Step 3: Run Pi diagnostics**
Launch `pi` inside the workspace and verify it starts up without any warnings and loads the skills.
