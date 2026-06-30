# 🧠 CK's Pi Harness Architecture Refactor Design Spec

*   **Status**: Approved (by user request)
*   **Author**: Antigravity (AI Coding Assistant)
*   **Date**: 2026-07-01
*   **Target Version**: v3.8.0

---

## 1. Context & Objectives

The current implementation of `CK's Pi Code Agent Harness` is designed to configure `badlogic/pi-mono` (Pi Coding Agent). However, it copies configuration paths of external submodules (such as `everything-claude-code`, `superpowers`, etc.) into `~/.pi/agent/config.json`. 

Through source code research of the `pi-mono` engine, we established that **Pi does not read `config.json`**. It only reads `settings.json`. As a result, all external submodules are currently completely ignored and offline.

Our objectives are:
1.  **Migrate Configuration to `settings.json`**: Integrate submodule paths directly into `~/.pi/agent/settings.json` (`skills` and `extensions` arrays).
2.  **Support Skill Profiles (Selection)**: Implement `minimal`, `standard` (default), and `full` profiles to prevent token budget exhaustion and skill collision warnings.
3.  **Fix `package.json` Warnings**: Remove non-existent skill paths from the project's root `package.json`.
4.  **Preserve User Custom Settings**: Use deep merge when restoring configurations so that user-defined settings (like local API bases and model selections) are never overwritten.
5.  **Clean Up Duplicate Shell Scripts**: Delegate `scripts/restore.sh` to `scripts/restore.py` to prevent split-brain maintenance issues.

---

## 2. Refactoring Details

### 2.1 `package.json`
Remove the invalid relative paths. Update the `"pi"` config block to list only directories that actually exist in the local project workspace.

**Before:**
```json
    "skills": [
      "pi-skills/core",
      "pi-skills/caveman",
      "pi-skills/chrome-cdp",
      "pi-skills/dev-browser",
      "pi-skills/using-superpowers",
      "pi-skills/writing-skills",
      "pi-skills/prompt-master",
      "pi-skills/optional"
    ]
```

**After:**
```json
    "skills": [
      "pi-skills/core",
      "pi-skills/chrome-cdp",
      "pi-skills/dev-browser",
      "pi-skills/optional"
    ]
```
*(Reason: `using-superpowers`, `writing-skills`, and `prompt-master` exist in `external/`, not in `pi-skills/`. They will be loaded globally via `settings.json` instead, eliminating project-level warning diagnostics).*

---

### 2.2 `pi-config/settings.json.example`
Provide template fields for `skills` and `extensions` arrays.
```json
{
  "packages": [
    "npm:context-mode"
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

---

### 2.3 `scripts/restore.py`

#### A. Read and Merge Settings
Instead of raw file copying, implement a deep merge function that loads the existing `~/.pi/agent/settings.json` (if it exists) and overlays the default settings from `pi-config/settings.json` without wiping out the user's custom provider/model settings.

#### B. Dynamic Submodule Paths Resolution
Map the submodules to full absolute paths and categorize them into profiles:

*   **`minimal`**:
    *   Skills: Only `pi-skills/core` (local) and `external/caveman/skills/caveman`.
    *   Extensions: `pi-extensions/ecc-hooks-bridge` (minimal profile env preset).
*   **`standard`** (Default):
    *   Skills: Core + Caveman (all 7 skills) + Superpowers (using-superpowers, brainstorming, writing-plans, test-driven-development, systematic-debugging, subagent-driven-development, executing-plans, verification-before-completion, finishing-a-development-branch, receiving-code-review, requesting-code-review, using-git-worktrees, writing-skills) + Karpathy Guidelines + Planning with Files + LLM Wiki + prompt-master.
    *   Extensions: `ecc-hooks-bridge` (standard profile) + `planning-with-files-bridge` + `pip-guardian` + `governance-bridge` + `evolution-bridge` + `aixbdd-bridge`.
*   **`full`**:
    *   Skills: Standard + Nuwa-Skill (Nuwa framework + 15 perspectives) + Matt Pocock skills + Addy Osmani skills + UI/UX Pro Max skills + Camoufox Stealth.
    *   Extensions: Standard + `omc-bridge` + `addyosmani-bridge` + `pm-skills-bridge` + `taste-bridge`.

#### C. Settings Generation
Write the resolved absolute paths directly into `settings["skills"]` and `settings["extensions"]` of `~/.pi/agent/settings.json`.

#### D. Cleanup
Delete `~/.pi/agent/config.json` if it exists.

---

### 2.4 `scripts/setup.py`
Add a command-line argument and interactive prompt for selecting the **Skill Profile**:
1.  **Minimal**: Only core bridges and caveman. Low memory/Ollama footprint.
2.  **Standard** (Recommended): Core + Superpowers + Karpathy + BDD + Security Hooks.
3.  **Full**: Loads everything including all 32+ OMC Agents, Nuwa personalities, Matt Pocock, and Addy Osmani skills.

Pass the selected profile as `--profile` parameter to `restore.py`.

---

### 2.5 `scripts/restore.sh`
Delegate execution directly to Python to avoid duplicate code logic:
```bash
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/restore.py" "$@"
```

---

## 3. Verification Plan

1.  **Dry Run / Run Setup**: Run `python scripts/setup.py` and select a profile.
2.  **Verify settings.json Output**: Confirm `~/.pi/agent/settings.json` contains:
    - User's custom model configurations (if any).
    - Absolute paths mapping to `external/...` in the `skills` and `extensions` arrays.
3.  **Verify config.json Removal**: Confirm `~/.pi/agent/config.json` has been deleted.
4.  **Verify Pi Diagnostics**: Launch `pi` and run a check to ensure all skills are loaded without warnings.
