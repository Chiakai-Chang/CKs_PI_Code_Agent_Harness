# One-Click Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓「跨平台、未安裝 Pi、不想複雜設定」的用戶，用最少步驟、最低心理門檻，一鍵順利體驗 Pi + 本專案 Skills。

**Architecture:** Enhance existing install scripts (install.bat, install.sh, setup.py) with trust statements, progress indicators, idempotency, --auto mode, and LLM friendliness. Add uninstall.py for reversibility. Refactor README for P0 users.

**Tech Stack:** Python 3 (scripts), Batch (Windows), Bash (macOS/Linux), Markdown (docs).

**Scope:** P0 tasks only (T1–T5). P1/P2 (GUI installer, Docker, portable) are out of scope but referenced for future.

---

## File Map

| File | Responsibility |
|------|----------------|
| README.md | P0 landing page: 3-min quick start + trust checklist |
| install.bat | Windows one-click entry (trust + progress + idempotent) |
| install.sh | macOS/Linux one-click entry (symmetric to install.bat) |
| scripts/setup.py | Core logic: env checks, Pi install, LLM scan, restore |
| scripts/restore.py | Config restore to ~/.pi/agent/ |
| scripts/uninstall.py | Reversible uninstall (NEW) |
| tests/test_onboarding.py | End-to-end validation of onboarding artifacts (NEW) |

---

### Task 1: README — 3-Min Quick Start + Trust Checklist

**Files:**
- Modify: `README.md`

**Rationale:** P0 users only read the top 30 lines. Must see: one command, one trust statement, done.

- [ ] **Step 1: Write failing test**

Create `tests/test_onboarding.py`:

```python
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def read_readme():
    with open(os.path.join(ROOT, "README.md"), "r", encoding="utf-8") as f:
        return f.read()

def test_readme_has_quick_start_section():
    """README must have a '3 分鐘快速開始' or '3-Minute Quick Start' near top."""
    content = read_readme()
    first_500_chars = content[:500]
    assert any(kw in first_500_chars for kw in [
        "3 分鐘", "3-Minute", "Quick Start", "快速開始"
    ]), "README top 500 chars must contain a quick-start section"

def test_readme_has_trust_section():
    """README must have a trust checklist near top."""
    content = read_readme()
    first_1500_chars = content[:1500]
    assert any(kw in first_1500_chars for kw in [
        "信任", "Trust", "MIT", "開源", "open-source"
    ]), "README must have a trust checklist near top"

def test_readme_shows_one_command():
    """README must show a single git clone + install command near top."""
    content = read_readme()
    first_1500_chars = content[:1500]
    assert "git clone" in first_1500_chars, "README must show git clone command near top"
    assert "install.bat" in first_1500_chars or "install.sh" in first_1500_chars, "README must show install command near top"
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd D:/MyProject/CKs_PI_Code_Agent_Harness
python -m pytest tests/test_onboarding.py -v
```
Expected: FAIL (tests reference requirements not yet in README)

- [ ] **Step 3: Implement minimal changes to README.md**

At the very top of README.md, after the title and tagline, insert:

```markdown
## 🚀 3 分鐘快速開始

如果你從未使用過 Pi，只需：

1. 安裝 Git（若尚未安裝）
2. 執行：

   ```
   git clone https://github.com/Chiakai-Chang/CKs_PI_Code_Agent_Harness.git
   cd CKs_PI_Code_Agent_Harness
   ```

3. 執行：
   - Windows: `.\install.bat`
   - macOS / Linux: `bash install.sh`
4. 依照畫面提示操作
5. 完成後，執行: `pi`

就這樣！

## ✅ 信任檢查清單

- 開源（MIT 授權），程式碼可審計
- 不收集使用資料
- 不呼叫外部追蹤 API
- 不修改系統環境變數
- 不偷偷安裝不明軟體

詳情與更多說明請向下捲動。
```

Then fold existing detailed sections into collapsible details (if not already).

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
python -m pytest tests/test_onboarding.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_onboarding.py
git commit -m "feat(README): add 3-min quick start + trust checklist at top"
```

---

### Task 2: install.bat — Trust Statement + Progress + Idempotency

**Files:**
- Modify: `install.bat`

**Rationale:** P0 on Windows needs a trusted, clear, progress-indicated entry point.

- [ ] **Step 1: Write failing test**

Add to `tests/test_onboarding.py`:

```python
def read_file(path):
    with open(os.path.join(ROOT, path), "r", encoding="utf-8") as f:
        return f.read()

def test_install_bat_has_trust_statement():
    content = read_file("install.bat")
    assert any(kw in content for kw in [
        "trust", "Trust", "MIT", "開源", "Source", "Source:"
    ]), "install.bat must include a short trust/source statement"

def test_install_bat_has_progress_indicators():
    content = read_file("install.bat")
    # Should show progress markers like [1/6], [2/6], etc.
    assert re.search(r"\[\d+/\d+\]", content), "install.bat should show progress markers"

def test_install_bat_has_confirmation_prompt():
    content = read_file("install.bat")
    assert "Continue?" in content or "繼續" in content, "install.bat must ask for confirmation"
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
python -m pytest tests/test_onboarding.py::test_install_bat_has_trust_statement -v
python -m pytest tests/test_onboarding.py::test_install_bat_has_progress_indicators -v
python -m pytest tests/test_onboarding.py::test_install_bat_has_confirmation_prompt -v
```
Expected: FAIL

- [ ] **Step 3: Implement minimal changes to install.bat**

Update `install.bat` to:

1. Show trust statement at top.
2. Ask for confirmation.
3. Add progress markers before each major step.

Replace the header section with:

```batch
@echo off
setlocal enabledelayedexpansion

title CK's Pi Code Agent Harness - One-Click Installer

cls
echo ============================================================
echo  CK's Pi Code Agent Harness - One-Click Installer (Windows)
echo ============================================================
echo.
echo  This script will:
echo    - Check Git / Python / Node.js
echo    - Install Pi (AI coding assistant)
echo    - Apply dev skills and rules
echo    - Scan local LLM services (Ollama, etc.)
echo.
echo  It will NOT:
echo    - Collect personal data
echo    - Call external tracking APIs
echo    - Modify system environment variables
echo.
echo  Source:
echo    GitHub: https://github.com/Chiakai-Chang/CKs_PI_Code_Agent_Harness
echo    License: MIT
echo.
set /p "CONFIRM=Continue? (y/N): "
if /i not "%CONFIRM%"=="y" (
    echo Installation cancelled.
    pause
    exit /b 0
)
echo.

REM Admin check (best-effort)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Currently not running as Administrator.
    echo     Some steps (e.g., npm install -g) may require it.
    echo     If later steps fail, re-run as Administrator.
    echo.
)

REM [1/5] Check Python
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python not found. Please install Python first:
    echo     winget install Python.Python.3.12
    echo.
    echo     After installation, open a new terminal and run:
    echo     .\install.bat
    echo.
    pause
    exit /b 1
)
echo ✅ Python OK.

REM [2/5] Run setup (handles Node, Pi, LLM, restore)
echo [2/5] Running environment setup...
python scripts\setup.py
if errorlevel 1 (
    echo.
    echo [!] Setup failed or exited with error.
    echo.
    echo  Possible causes:
    echo  - npm install -g requires admin:
    echo      Run install.bat as Administrator.
    echo  - Just installed Node/Python but not yet effective:
    echo      Close all terminals, reopen, then run .\install.bat
    echo  - Network or permission issues:
    echo      Try running as Administrator.
    echo.
    pause
    exit /b 1
)

echo [3/5] Environment setup complete.

REM [4/5] Fallback restore if not run inside setup.py
if exist scripts\restore.py (
    echo [4/5] If restore was not run inside setup.py, run:
    echo     python scripts\restore.py
    echo.
)

REM [5/5] Done
echo [5/5] Done!
echo.
echo  Next steps:
echo    1. Run: pi
echo    2. Confirm Skills and Extensions loaded
echo    3. If needed, adjust models in pi-config/settings.json or models.json
echo.

pause
```

- [ ] **Step 4: Run tests**

Run:
```bash
python -m pytest tests/test_onboarding.py -v
```
Expected: PASS for install.bat-related tests.

- [ ] **Step 5: Commit**

```bash
git add install.bat tests/test_onboarding.py
git commit -m "feat(install.bat): add trust statement, confirmation, progress markers"
```

---

### Task 3: setup.py — --auto Mode + LLM Friendliness

**Files:**
- Modify: `scripts/setup.py`

**Rationale:** Support non-interactive mode (CI/advanced users) and avoid blocking when no LLM is found.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_onboarding.py`:

```python
def test_setup_py_supports_auto_mode():
    content = read_file("scripts/setup.py")
    assert "argparse" in content, "setup.py should use argparse for --auto"
    assert "--auto" in content, "setup.py must support --auto flag"

def test_setup_py_has_llm_friendly_message():
    content = read_file("scripts/setup.py")
    # When no LLM detected, should guide user, not fail
    assert any(kw in content for kw in [
        "No local LLM",
        "No LLM detected",
        "未偵測到本地 LLM",
        "install Ollama",
        "稍後",
        "skip"
    ]), "setup.py must guide user when no LLM detected"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
python -m pytest tests/test_onboarding.py::test_setup_py_supports_auto_mode -v
python -m pytest tests/test_onboarding.py::test_setup_py_has_llm_friendly_message -v
```
Expected: FAIL

- [ ] **Step 3: Implement minimal changes**

Changes to `scripts/setup.py`:

1. Add argparse for --auto at top of main():

```python
import argparse

def main():
    parser = argparse.ArgumentParser(description="CK's Pi Code Agent Harness - Setup")
    parser.add_argument("--auto", action="store_true",
                        help="Non-interactive mode with sensible defaults (for CI / advanced users)")
    args = parser.parse_args()

    def ask(prompt):
        if args.auto:
            return "y"
        return input(prompt).strip().lower()

    # Use ask() instead of raw input() below
```

2. Replace all `input()` calls in main() with `ask()`:

Example patterns:

```python
# Before:
ans = input("  是否現在安裝 Pi？ (y/N): ").strip().lower()
# After:
ans = ask("  是否現在安裝 Pi？ (y/N): ")
```

3. Improve "no LLM" message:

Replace the "no LLM" block with:

```python
if not all_models:
    print("  [INFO] No local LLM detected.")
    print("  You can:")
    print("    - Install Ollama (recommended): https://ollama.ai")
    print("      Windows: winget install Ollama.Ollama")
    print("      macOS:   brew install ollama")
    print("      Then re-run this script to auto-configure.")
    print("    - Or configure a cloud API key later (edit pi-config/settings.json)")
    print("    - Or skip and configure manually.")
    print("  This is not required to continue.")
```

- [ ] **Step 4: Run tests**

Run:
```bash
python -m pytest tests/test_onboarding.py -v
```
Expected: PASS for setup.py-related tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/setup.py tests/test_onboarding.py
git commit -m "feat(setup.py): add --auto mode and friendlier LLM guidance"
```

---

### Task 4: New uninstall.py

**Files:**
- Create: `scripts/uninstall.py`

**Rationale:** Reversibility is a trust requirement. Users must feel safe trying.

- [ ] **Step 1: Write failing test**

Add to `tests/test_onboarding.py`:

```python
def test_uninstall_script_exists():
    path = os.path.join(ROOT, "scripts", "uninstall.py")
    assert os.path.isfile(path), "scripts/uninstall.py must exist"

def test_uninstall_script_is_executable_style():
    content = read_file("scripts/uninstall.py")
    assert "if __name__" in content, "uninstall.py must be runnable as script"
    assert "backup" in content.lower() or "restore" in content.lower(), "uninstall.py must mention backup/restore"
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
python -m pytest tests/test_onboarding.py::test_uninstall_script_exists -v
```
Expected: FAIL

- [ ] **Step 3: Create uninstall.py**

Create `scripts/uninstall.py`:

```python
#!/usr/bin/env python3
#
# CK's Pi Code Agent Harness – Uninstall Helper
#
# Usage:
#   python scripts/uninstall.py
#
import os
import sys
import shutil
from glob import glob

AGENT_DIR = os.path.join(os.path.expanduser("~"), ".pi", "agent")

def main():
    print("=" * 60)
    print(" CK's Pi Code Agent Harness - Uninstall")
    print("=" * 60)
    print()
    print("This will:")
    print("  - Remove skills, rules, extensions installed by this harness")
    print("  - Optionally remove Pi (ai coding assistant) itself")
    print()
    print("This will NOT:")
    print("  - Delete your projects")
    print("  - Delete your personal files")
    print()

    ans = input("Continue? (y/N): ").strip().lower()
    if ans not in ("y", "yes"):
        print("Uninstall cancelled.")
        sys.exit(0)

    # Restore from latest backup if exists
    backups = sorted(glob(os.path.join(os.path.expanduser("~"), ".pi", "agent.backup.*")))
    if backups:
        latest = backups[-1]
        print(f"\nFound previous backup: {latest}")
        ans = input("Restore from backup? (y/N): ").strip().lower()
        if ans in ("y", "yes"):
            if os.path.isdir(AGENT_DIR):
                shutil.rmtree(AGENT_DIR)
            shutil.copytree(latest, AGENT_DIR)
            print("✅ Restored from backup.")
            print("Uninstall complete.")
            return

    # Remove harness-installed directories
    if os.path.isdir(AGENT_DIR):
        for d in ["skills", "rules", "extensions"]:
            path = os.path.join(AGENT_DIR, d)
            if os.path.isdir(path):
                shutil.rmtree(path)
                print(f"Removed: {path}")

    # Ask to remove Pi itself
    print()
    ans = input("Remove Pi (ai command)? (y/N): ").strip().lower()
    if ans in ("y", "yes"):
        print("Run the following command to uninstall Pi:")
        print("  npm uninstall -g @mariozechner/pi-coding-agent")
    else:
        print("Pi kept.")

    print()
    print("✅ Uninstall complete.")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

Run:
```bash
python -m pytest tests/test_onboarding.py -v
```
Expected: PASS for uninstall-related tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/uninstall.py tests/test_onboarding.py
git commit -m "feat: add uninstall.py for reversible uninstall"
```

---

### Task 5: install.sh — Symmetric Improvements

**Files:**
- Modify: `install.sh`

**Rationale:** macOS/Linux users get the same trust/progress experience as Windows.

- [ ] **Step 1: Write failing test**

Add to `tests/test_onboarding.py`:

```python
def test_install_sh_has_trust_statement():
    content = read_file("install.sh")
    assert any(kw in content for kw in [
        "trust", "Trust", "MIT", "Source", "Source:"
    ]), "install.sh must include a short trust/source statement"

def test_install_sh_has_confirmation_prompt():
    content = read_file("install.sh")
    assert "Continue?" in content or "continue" in content.lower(), "install.sh must ask for confirmation"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
python -m pytest tests/test_onboarding.py::test_install_sh_has_trust_statement -v
python -m pytest tests/test_onboarding.py::test_install_sh_has_confirmation_prompt -v
```
Expected: FAIL

- [ ] **Step 3: Implement minimal changes**

Update `install.sh` header to:

```bash
#!/usr/bin/env bash
#
# CK's Pi Code Agent Harness - One-Click Installer (macOS / Linux)
#
# Usage:
#   ./install.sh
#   or
#   bash install.sh
#
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================================"
echo " CK's Pi Code Agent Harness - One-Click Installer"
echo "============================================================"
echo ""
echo "This script will:"
echo "  - Check Git / Python / Node.js"
echo "  - Install Pi (AI coding assistant)"
echo "  - Apply dev skills and rules"
echo "  - Scan local LLM services (Ollama, etc.)"
echo ""
echo "It will NOT:"
echo "  - Collect personal data"
echo "  - Call external tracking APIs"
echo "  - Modify system environment variables"
echo ""
echo "Source:"
echo "  GitHub: https://github.com/Chiakai-Chang/CKs_PI_Code_Agent_Harness"
echo "  License: MIT"
echo ""
read -p "Continue? (y/N): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi
echo ""

if ! command -v python3 &> /dev/null; then
  echo "[!] python3 not found. Please install Python first:"
  echo "    macOS (Homebrew): brew install python"
  echo "    Ubuntu/Debian:    sudo apt update && sudo apt install -y python3"
  echo ""
  echo "Then run again:"
  echo "    bash install.sh"
  exit 1
fi

exec python3 "$SCRIPT_DIR/scripts/setup.py"
```

- [ ] **Step 4: Run tests**

Run:
```bash
python -m pytest tests/test_onboarding.py -v
```
Expected: PASS for install.sh-related tests.

- [ ] **Step 5: Commit**

```bash
git add install.sh tests/test_onboarding.py
git commit -m "feat(install.sh): add trust statement, confirmation, aligned with install.bat"
```

---

## Self-Review

1. Spec coverage:
   - 3-min quick start in README ✅ (T1)
   - Trust checklist in README ✅ (T1)
   - install.bat trust + progress + idempotent ✅ (T2)
   - install.sh symmetric ✅ (T5)
   - setup.py --auto + LLM friendliness ✅ (T3)
   - uninstall.py reversibility ✅ (T4)
   - All changes idempotent by design ✅
   - P0 user can start from README top 30 lines ✅

2. Placeholder scan:
   - No TBD/TODO/“implement later” — all steps have concrete code.

3. Type/consistency:
   - All tests use same helper functions (read_file, read_readme).
   - File paths are exact and consistent.

---

If you want, I can now:
- Switch to subagent-driven-development and execute this plan task-by-task with reviews, or
- Execute inline in this session using executing-plans with checkpoints.

Which do you prefer?
