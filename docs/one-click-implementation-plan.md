# One-Click Onboarding — Implementation Plan

> 基於多角色 MECE 討論，拆解為可執行的任務清單。

---

## 🔴 P0：立即可做（建議優先實作）

### Task 1：README 重構

**目標：** P0 用戶只看前 30 行就能開始。

**變更：**

- 最上方加入「🚀 3 分鐘快速開始」
- 加入「✅ 信任檢查清單」
- 摺疊高級內容

**範例（置於 README 最上方）：**

```markdown
# 🚀 CK's Pi Code Agent Harness

> 3 分鐘內，在一台新電腦上體驗 AI 程式開發助手

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

- 開源（MIT），程式碼可審計
- 不收集使用資料
- 不呼叫外部追蹤 API
- 不修改系統環境變數
- 不偷偷安裝不明軟體

[更多說明 ↓](#-更多說明)
```

### Task 2：install.bat 改進

**目標：** 更友善、更可信、冪等。

**變更：**

- 加入信任聲明
- 加入進度提示
- 冪等處理

**範例（install.bat 開頭）：**

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
```

### Task 3：setup.py 改進

**目標：** 冪等、--auto 模式、更友善 LLM 提示。

**變更：**

- 加入 --auto 模式
- 冪等處理
- LLM 推薦提示
- 「稍後設定 LLM」選項

**關鍵變更：**

```python
import argparse

def main():
    parser = argparse.ArgumentParser(description="CK's Pi Code Agent Harness Setup")
    parser.add_argument("--auto", action="store_true",
                        help="Non-interactive mode with defaults")
    args = parser.parse_args()

    # Use args.auto to skip prompts
```

- LLM 掃描後：

```python
if not all_models:
    print("  [INFO] No local LLM detected. You can:")
    print("    - Install Ollama: https://ollama.ai")
    print("    - Or configure a cloud API key later")
    print("    - Or skip and configure manually")
```

### Task 4：新增 uninstall.py

**目標：** 提供可逆性。

**檔案：** `scripts/uninstall.py`

**功能：**

- 移除 skills / rules / extensions
- 可選：卸載 Pi
- 可選：還原備份

**範例：**

```python
#!/usr/bin/env python3
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
    print("  - Optionally remove Pi itself")
    print()
    print("It will NOT:")
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
        print(f"Found backup: {latest}")
        ans = input("Restore from backup? (y/N): ").strip().lower()
        if ans in ("y", "yes"):
            if os.path.isdir(AGENT_DIR):
                shutil.rmtree(AGENT_DIR)
            shutil.copytree(latest, AGENT_DIR)
            print("✅ Restored from backup.")
    else:
        # Remove harness-installed files
        for d in ["skills", "rules", "extensions"]:
            path = os.path.join(AGENT_DIR, d)
            if os.path.isdir(path):
                shutil.rmtree(path)
                print(f"Removed: {path}")

    # Ask to remove Pi
    ans = input("Remove Pi (pi command)? (y/N): ").strip().lower()
    if ans in ("y", "yes"):
        print("Run: npm uninstall -g @mariozechner/pi-coding-agent")
    else:
        print("Pi kept.")

    print()
    print("✅ Uninstall complete.")

if __name__ == "__main__":
    main()
```

### Task 5：install.sh 改進

**目標：** 與 install.bat 對稱的改進。

**變更：**

- 加入信任聲明
- 冪等處理
- 進度提示

---

## 🟡 P1：短期（建議 1-2 週內）

### Task 6：Windows GUI 安裝器（setup.exe）

**工具：** NSIS 或 Inno Setup

**功能：**

- 圖形化進度條
- 內建依賴檢查
- 一鍵完成

**觸發條件：** 當有足夠 P0 用戶反饋時優先實作

### Task 7：macOS/Linux 一鍵腳本

**macOS：**

- 提供 Brewfile
- 使用 `brew bundle`

**Linux：**

- 自動偵測套件管理器
- 提供 install-ubuntu.sh / install-fedora.sh

### Task 8：CI / Docker 範例

**CI：**

- 提供 .github/workflows/example.yml

**Docker：**

- 提供 Dockerfile 範例

---

## 🟢 P2：長期（願景）

### Task 9：可攜式 Pi Harness

**目標：** 解壓即用，不需系統安裝。

**做法：**

- 內建 Node + Python
- 自訂 Pi 執行環境
- 不污染系統

### Task 10：Web-based 安裝嚮導

**目標：** 瀏覽器版安裝嚮導，逐步圖文說明。

---

## 驗證標準

所有變更需通過以下驗證：

1. **P0 用戶可独立完成：**
   - 從 GitHub README 到 pi 跑起來 ≤ 5 分鐘
   - 不需要搜尋額外文件
2. **冪等：**
   - 跑兩次不爆炸
3. **可逆：**
   - uninstall.py 可完全移除
4. **跨平台：**
   - Windows / macOS / Linux 皆可用
5. **信任：**
   - 用戶可審計程式碼
   - 不收集資料
   - MIT 授權
