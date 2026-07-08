# 一鍵更新 + 完整刪除 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 加 `setup.py --mode update`（git pull + restore + pi update 一鍵）、雙擊 `update.bat`/`update.sh`，與 `uninstall.py --purge`（逐項確認的完整刪除），面向一般使用者。

**Architecture:** 沿用既有 `setup.py` mode 架構新增 update 模式與選單項；新增兩個薄啟動腳本；`uninstall.py` 引入 argparse 加 `--purge`。全部零依賴、破壞性動作預設否。

**Tech Stack:** Python 3 標準庫、Windows CMD (`update.bat`)、POSIX sh (`update.sh`)、unittest。

## Global Constraints

- 零依賴（Python 標準庫）；測試 `unittest`，不引入 pytest。
- 破壞性動作預設否；`--auto`/非 tty 一律跳過刪除。
- pi npm scope 一律 `@earendil-works/pi-coding-agent`（舊 `@mariozechner` 凍結）。
- 不硬編機器路徑（無 `[A-Za-z]:/MyProject`、`file:///`）。
- 本機 Python：`C:/Users/User/AppData/Local/Python/bin/python.exe`（`python` 為失效 stub）。
- Git 身分已設 `Chiakai Chang <lotifv@gmail.com>`。

## File Structure

- `scripts/setup.py` — 加 `update` mode：`--mode` choices、選單 `[4]`、`run_update()`、main() 分派。
- `update.bat` / `update.sh` — 雙擊入口，呼叫 `setup.py --mode update`。
- `scripts/uninstall.py` — argparse + `ask()` + `--purge` 區塊 + 修正 pi scope。
- `README.md` — 更新與升級段落改寫、新增解除安裝段。
- `tests/test_update_purge.py` — 零依賴 unittest。

---

### Task 1: `setup.py --mode update`

**Files:**
- Modify: `scripts/setup.py`
- Test: `tests/test_update_purge.py`

**Interfaces:**
- Produces: `run_update()`（無參數，內部用既有 `REPO_ROOT`/`sys.executable`/`run_stream`/`has_command`）；`--mode update`；選單 `[4]`。

- [ ] **Step 1: 寫失敗測試**

新建 `tests/test_update_purge.py`：

```python
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_file(rel):
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as f:
        return f.read()


class TestSetupUpdateMode(unittest.TestCase):
    def test_update_in_choices(self):
        c = read_file("scripts/setup.py")
        self.assertIn('choices=["full", "model", "restore", "update"]', c)

    def test_menu_has_option_4(self):
        c = read_file("scripts/setup.py")
        self.assertIn("[4] 更新", c)
        self.assertIn('if ans == "4": return "update"', c)

    def test_run_update_flow(self):
        c = read_file("scripts/setup.py")
        self.assertIn("def run_update", c)
        i = c.find("def run_update")
        blk = c[i:i + 800]
        self.assertIn("git pull --recurse-submodules", blk)
        self.assertIn("restore.py", blk)
        self.assertIn("pi update --all", blk)

    def test_update_dispatched(self):
        c = read_file("scripts/setup.py")
        self.assertIn('if mode == "update":', c)
        self.assertIn("run_update()", c)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_update_purge.TestSetupUpdateMode -v`
Expected: FAIL（choices 尚未含 update 等）

- [ ] **Step 3: 實作**

在 `scripts/setup.py`：

(a) 定義 `run_update()`（放在 `has_command` 之後、`load_json` 之前皆可；緊接 `ask()` 之後最自然）：

```python
def run_update():
    """One-command update: pull repo+submodules, resync config, update Pi."""
    print("[*] 正在更新 Harness 與子模組 (git pull)...")
    run_stream("git pull --recurse-submodules")
    restore_script = os.path.join(REPO_ROOT, "scripts", "restore.py")
    print("[*] 正在重新同步配置 (restore --auto，冪等、保留自訂)...")
    run_stream(f'"{sys.executable}" "{restore_script}" --auto')
    if has_command("pi"):
        print("[*] 正在更新 Pi 本體與擴充 (pi update --all)...")
        run_stream("pi update --all")
    else:
        print("[*] 未偵測到 pi，略過。裝好後可自行執行: pi update --all")
    print("\n" + "=" * 60 + "\n 更新完成！請執行: pi\n" + "=" * 60)
```

(b) `show_main_menu()` — 改選單列與輸入範圍、加 `4`：

找到：
```python
    print("\n [1] 完整安裝 [2] 切換模型 [3] 僅還原配置 [Q] 離開")
    ans = input("\n請輸入編號 (1-3, Q): ").strip().lower()
    if ans == "1": return "full"
    if ans == "2": return "model"
    if ans == "3": return "restore"
```
改為：
```python
    print("\n [1] 完整安裝 [2] 切換模型 [3] 僅還原配置 [4] 更新 [Q] 離開")
    ans = input("\n請輸入編號 (1-4, Q): ").strip().lower()
    if ans == "1": return "full"
    if ans == "2": return "model"
    if ans == "3": return "restore"
    if ans == "4": return "update"
```

(c) `--mode` choices：
找到：
```python
    parser.add_argument("--mode", choices=["full", "model", "restore"])
```
改為：
```python
    parser.add_argument("--mode", choices=["full", "model", "restore", "update"])
```

(d) main() 分派 — 在設定 git safe.directory 之後、`if mode in ["full", "restore"]:`（submodule 區塊）之前插入：
```python
    if mode == "update":
        run_update()
        return
```

- [ ] **Step 4: 跑測試確認通過 + 編譯**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_update_purge.TestSetupUpdateMode -v`
Expected: PASS

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m py_compile scripts/setup.py`
Expected: 無輸出

- [ ] **Step 5: Commit**

```bash
git add scripts/setup.py tests/test_update_purge.py
git commit -m "feat(setup): add one-command --mode update (pull + restore + pi update)"
```

---

### Task 2: 雙擊入口 `update.bat` / `update.sh`

**Files:**
- Create: `update.bat`
- Create: `update.sh`
- Test: `tests/test_update_purge.py`

**Interfaces:**
- Consumes: Task 1 的 `--mode update`。

- [ ] **Step 1: 寫失敗測試**

在 `tests/test_update_purge.py` 追加：

```python
class TestUpdateEntryScripts(unittest.TestCase):
    def test_update_bat(self):
        c = read_file("update.bat")
        self.assertIn("--mode update", c)
        self.assertIn("chcp 65001", c)

    def test_update_sh(self):
        c = read_file("update.sh")
        self.assertIn("--mode update", c)

    def test_no_machine_paths(self):
        import re
        for f in ("update.bat", "update.sh"):
            self.assertIsNone(
                re.search(r"[A-Za-z]:/MyProject|file:///", read_file(f)),
                f"{f} must not contain machine-specific paths",
            )
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_update_purge.TestUpdateEntryScripts -v`
Expected: FAIL（檔案不存在）

- [ ] **Step 3: 建立檔案**

`update.bat`：
```bat
@echo off
chcp 65001 > nul

REM ============================================================
REM  CK's Pi Code Agent Harness - Updater
REM  Trust / License: MIT licensed open-source project.
REM ============================================================

echo [1/1] Updating (git pull + restore + pi update)...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 找不到 Python。請先安裝 Python 並加入 PATH。
    pause
    exit /b 1
)

python "%~dp0scripts\setup.py" --mode update
pause
```

`update.sh`：
```sh
#!/usr/bin/env bash
#
# CK's Pi Code Agent Harness - Updater
# License: MIT (open-source)
#
set -e

if ! command -v python3 &> /dev/null; then
    echo "[!] python3 not found. Please install Python first."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/scripts/setup.py" --mode update
```

- [ ] **Step 4: 跑測試確認通過 + 語法**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_update_purge.TestUpdateEntryScripts -v`
Expected: PASS

Run: `sh -n update.sh`
Expected: 無輸出

- [ ] **Step 5: Commit**

```bash
git add update.bat update.sh tests/test_update_purge.py
git commit -m "feat: add update.bat / update.sh double-click updaters"
```

---

### Task 3: `uninstall.py --purge`

**Files:**
- Modify: `scripts/uninstall.py`
- Test: `tests/test_update_purge.py`

**Interfaces:**
- Produces: `--purge` 旗標、`ask(prompt, default="n")` helper、`_purge()`；修正 pi scope 為 `@earendil-works/pi-coding-agent`。

- [ ] **Step 1: 寫失敗測試**

在 `tests/test_update_purge.py` 追加：

```python
class TestUninstallPurge(unittest.TestCase):
    REL = "scripts/uninstall.py"

    def test_argparse_and_flag(self):
        c = read_file(self.REL)
        self.assertIn("import argparse", c)
        self.assertIn('"--purge"', c)

    def test_purge_targets(self):
        c = read_file(self.REL)
        self.assertIn(".camofox", c)
        self.assertIn("agent.backup", c)

    def test_scope_fixed(self):
        c = read_file(self.REL)
        self.assertIn("@earendil-works/pi-coding-agent", c)
        self.assertNotIn("@mariozechner", c)

    def test_ask_helper_nontty_safe(self):
        c = read_file(self.REL)
        self.assertIn("def ask", c)
        self.assertIn("isatty", c)
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_update_purge.TestUninstallPurge -v`
Expected: FAIL

- [ ] **Step 3: 實作**

在 `scripts/uninstall.py`：

(a) 匯入區加：
```python
import argparse
import subprocess
```

(b) 在 `main()` 之前新增 helper 與 `_purge()`：
```python
def ask(prompt, default="n"):
    """Interactive y/N that degrades to default (no) in non-tty runs — never deletes unattended."""
    if not sys.stdin.isatty():
        print(f"{prompt}{default} (auto)")
        return default
    try:
        return input(prompt).strip().lower()
    except EOFError:
        return default


def _purge():
    """Full clean-slate: each destructive step confirmed, default No."""
    print()
    print("[--purge] 完整刪除 — 逐項確認 (預設 N):")
    home = os.path.expanduser("~")
    if ask("刪除 ~/.camofox（登入 profile/cookies + Camoufox 快取）? [y/N]: ") in ("y", "yes"):
        remove_path(os.path.join(home, ".camofox"))
    if ask("刪除 restore 備份 ~/.pi/agent.backup.*? [y/N]: ") in ("y", "yes"):
        for b in glob(os.path.join(home, ".pi", "agent.backup.*")):
            remove_path(b)
    if ask("執行 npm uninstall -g @earendil-works/pi-coding-agent? [y/N]: ") in ("y", "yes"):
        try:
            subprocess.run("npm uninstall -g @earendil-works/pi-coding-agent", shell=True)
        except Exception as e:
            print(f"  npm uninstall 失敗: {e}；可手動執行。")
    else:
        print("  可手動執行: npm uninstall -g @earendil-works/pi-coding-agent")
    print()
    print(f"最後一步（程式無法自刪所在目錄）：請手動刪除 repo 資料夾：{REPO_ROOT}")
```

(c) `main()` 起始加 argparse，並把 `Continue?`、`Restore from backup?` 與 pi 提示改為 non-tty 安全 / 跳過。將 `main()` 由：
```python
def main():
    print("=" * 60)
    print(" CK's Pi Code Agent Harness - Uninstall")
    print("=" * 60)
    print()
    print("This will:")
    print("  - Remove skills, rules, extensions installed by this harness")
    print("  - Remove harness entries from settings.json")
    print("  - Optionally remove Pi (AI coding assistant) itself")
    print()
    print("This will NOT:")
    print("  - Delete your projects")
    print("  - Delete your personal files")
    print("  - Delete skills or extensions you installed yourself")
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

    # Remove only harness-managed items, preserving the user's own assets
    if os.path.isdir(AGENT_DIR):
        for name in MANAGED_SKILLS:
            remove_path(os.path.join(AGENT_DIR, "skills", name))
        for name in MANAGED_BRIDGES:
            remove_path(os.path.join(AGENT_DIR, "extensions", name))
        # rules/ and the global AGENTS.md are fully harness-managed (restore.py
        # clears and rewrites them wholesale)
        remove_path(os.path.join(AGENT_DIR, "rules"))
        remove_path(os.path.join(AGENT_DIR, "AGENTS.md"))
        clean_settings()

    # Ask to remove Pi itself
    print()
    ans = input("Remove Pi (pi command)? (y/N): ").strip().lower()
    if ans in ("y", "yes"):
        print("Run the following command to uninstall Pi:")
        print("  npm uninstall -g @mariozechner/pi-coding-agent")
    else:
        print("Pi kept.")

    print()
    print("✅ Uninstall complete.")
```
改為：
```python
def main():
    parser = argparse.ArgumentParser(description="CK's Pi Code Agent Harness - Uninstall")
    parser.add_argument("--purge", action="store_true",
                        help="Also remove ~/.camofox, restore backups, and optionally Pi itself")
    args = parser.parse_args()

    print("=" * 60)
    print(" CK's Pi Code Agent Harness - Uninstall" + (" (--purge)" if args.purge else ""))
    print("=" * 60)
    print()
    print("This will:")
    print("  - Remove skills, rules, extensions installed by this harness")
    print("  - Remove harness entries from settings.json")
    if args.purge:
        print("  - [--purge] Also offer to remove ~/.camofox, backups, and Pi")
    print()
    print("This will NOT:")
    print("  - Delete your projects")
    print("  - Delete your personal files")
    print("  - Delete skills or extensions you installed yourself")
    print()

    if ask("Continue? (y/N): ") not in ("y", "yes"):
        print("Uninstall cancelled.")
        sys.exit(0)

    # Restore from latest backup if exists (skipped under --purge: purge is a
    # clean-slate path, not a restore).
    backups = sorted(glob(os.path.join(os.path.expanduser("~"), ".pi", "agent.backup.*")))
    if backups and not args.purge:
        latest = backups[-1]
        print(f"\nFound previous backup: {latest}")
        if ask("Restore from backup? (y/N): ") in ("y", "yes"):
            if os.path.isdir(AGENT_DIR):
                shutil.rmtree(AGENT_DIR)
            shutil.copytree(latest, AGENT_DIR)
            print("✅ Restored from backup.")
            print("Uninstall complete.")
            return

    # Remove only harness-managed items, preserving the user's own assets
    if os.path.isdir(AGENT_DIR):
        for name in MANAGED_SKILLS:
            remove_path(os.path.join(AGENT_DIR, "skills", name))
        for name in MANAGED_BRIDGES:
            remove_path(os.path.join(AGENT_DIR, "extensions", name))
        # rules/ and the global AGENTS.md are fully harness-managed (restore.py
        # clears and rewrites them wholesale)
        remove_path(os.path.join(AGENT_DIR, "rules"))
        remove_path(os.path.join(AGENT_DIR, "AGENTS.md"))
        clean_settings()

    if args.purge:
        _purge()
    else:
        print()
        if ask("Remove Pi (pi command)? (y/N): ") in ("y", "yes"):
            print("Run the following command to uninstall Pi:")
            print("  npm uninstall -g @earendil-works/pi-coding-agent")
        else:
            print("Pi kept.")

    print()
    print("✅ Uninstall complete.")
```

- [ ] **Step 4: 跑測試確認通過 + 編譯**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_update_purge.TestUninstallPurge -v`
Expected: PASS

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m py_compile scripts/uninstall.py`
Expected: 無輸出

- [ ] **Step 5: Commit**

```bash
git add scripts/uninstall.py tests/test_update_purge.py
git commit -m "feat(uninstall): add --purge full clean-slate; fix stale pi npm scope"
```

---

### Task 4: README 文檔 + 全套驗證

**Files:**
- Modify: `README.md`
- Test: `tests/` 全部

**Interfaces:**
- Consumes: Task 1–3 成品。

- [ ] **Step 1: 寫失敗測試**

在 `tests/test_update_purge.py` 追加：

```python
class TestReadmeUpdatePurge(unittest.TestCase):
    def test_readme_mentions_update_and_uninstall(self):
        c = read_file("README.md")
        self.assertIn("update.bat", c)
        self.assertIn("--mode update", c)
        self.assertIn("--purge", c)
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_update_purge.TestReadmeUpdatePurge -v`
Expected: FAIL

- [ ] **Step 3: 改 README**

找到現有「### 3. 更新與升級 (Update)」整段：
```markdown
### 3. 更新與升級 (Update)
已安裝過的使用者，更新到最新版只需三步（設定與自訂技能都會被保留）：
```bash
git pull --recurse-submodules          # 1. 更新 Harness 與子模組
python scripts/setup.py --mode restore # 2. 重新同步配置（冪等，保留使用者自訂）
pi update --all                        # 3. 更新 Pi 本體與擴充套件（僅更新本體用 pi update）
```
> 啟動時若見到 `[Skill conflicts]` 名稱警告，多為上游命名問題、技能仍正常載入，詳見 [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)。
```
替換為：
```markdown
### 3. 更新與升級 (Update)
已安裝過的使用者一鍵更新（設定與自訂技能都會保留）：
*   **Windows**：雙擊 `update.bat`
*   **macOS / Linux**：執行 `bash update.sh`
*   **進階（等同上述）**：`python scripts/setup.py --mode update`
    — 內部自動執行 `git pull --recurse-submodules` → `restore --auto` → `pi update --all`。
> 啟動時若見到 `[Skill conflicts]` 名稱警告，多為上游命名問題、技能仍正常載入，詳見 [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)。

### 解除安裝 (Uninstall)
*   **只移除 harness 管理項**（保留你自己的技能與 `~/.camofox` 登入資料）：`python scripts/uninstall.py`
*   **完整刪除、重來**（逐項確認，可額外刪 `~/.camofox`、備份、Pi 本體）：`python scripts/uninstall.py --purge`
    — 最後會提示手動刪除 repo 資料夾。
```
（若你機器上 `### 3.` 後續的「### 4. 模式選擇」標題需順移，維持既有編號即可，不必改動其他段。）

- [ ] **Step 4: 全套測試 + 驗證**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest discover -s tests -v`
Expected: 全綠（含既有 + 新 test_update_purge）

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m py_compile scripts/setup.py scripts/uninstall.py`
Run: `sh -n update.sh`
Expected: 皆無輸出

手動冒煙（非 tty 破壞性安全）：
```bash
mkdir -p /tmp/sbpurge/.camofox
HOME=/tmp/sbpurge USERPROFILE=/tmp/sbpurge \
  C:/Users/User/AppData/Local/Python/bin/python.exe scripts/uninstall.py --purge </dev/null
ls /tmp/sbpurge/.camofox
```
Expected: 非 tty → `ask` 回傳預設 `n` → `Continue?` 即 `n (auto)`、流程取消；`~/.camofox` **仍在**（破壞性動作永不在非 tty 誤觸）。

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_update_purge.py
git commit -m "docs(readme): one-command update.bat/--mode update + uninstall --purge"
```

---

## Self-Review

**1. Spec coverage：**
- `--mode update`（choices+menu+run_update+dispatch）→ Task 1。
- run_update 全自動 git pull + restore --auto + pi update --all（pi 缺跳過）→ Task 1 Step 3(a)。
- profile 未持久化用 restore 預設 → run_update 用 `restore --auto`（預設 standard），spec 已註。
- 雙擊 update.bat/sh（不提權）→ Task 2。
- uninstall argparse + --purge + 逐項確認（camofox/backups/npm uninstall）+ 手動刪 repo 提示 → Task 3。
- pi scope 修正 @mariozechner→@earendil-works → Task 3（含反向斷言 assertNotIn）。
- 非 tty 破壞性預設 N（ask helper）→ Task 3 + Task 4 冒煙。
- README 更新/解除安裝段 → Task 4。
- 零依賴測試 → 各 Task。無缺口。

**2. Placeholder scan：** 無 TBD/TODO；所有程式步驟附完整內容與具體 old→new。

**3. Type consistency：** `run_update()`、`ask(prompt, default="n")`、`_purge()`、`--mode update`、`@earendil-works/pi-coding-agent`、`--purge` 全計畫一致；`REPO_ROOT`/`AGENT_DIR`/`remove_path`/`glob`/`run_stream`/`has_command`/`sys.executable` 均為既有符號。
