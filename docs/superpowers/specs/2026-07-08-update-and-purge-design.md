# 一鍵更新 + 完整刪除 設計 (2026-07-08)

> 為既有使用者加「一鍵更新」（`setup.py --mode update` + 雙擊 `update.bat`/`update.sh`）與「完整刪除」（`uninstall.py --purge`），面向一般使用者，不需背 CLI。

## 目標 (Goal)
既有使用者原地更新到最新版（拉 repo+子模組、同步配置、更新 Pi），一個動作完成；想徹底重來者有一條乾淨、逐項確認的完整刪除路徑。

## 非目標 (Non-Goals)
- 不改 Pi 官方 `pi update` 行為（無法掛入；只在我們的 update 流程中呼叫它）。
- 不自動刪除 repo 所在資料夾（程式不可靠地自刪 CWD；改為提示使用者手動刪）。
- 不改動既有 full/model/restore 模式的行為。

## Global Constraints
- 零依賴（Python 標準庫）；測試用 `unittest`（不引入 pytest）。
- bash/CMD 相容；`update.bat` 為 Windows CMD、`update.sh` 為 POSIX。
- 平台無關：不硬編機器路徑。
- 破壞性動作預設否（`--auto`/非 tty 一律跳過刪除）；每項單獨確認。
- pi npm scope 一律用新版 `@earendil-works/pi-coding-agent`（舊 `@mariozechner` 已凍結）。
- 本機 Python：`C:/Users/User/AppData/Local/Python/bin/python.exe`（`python` 為失效 stub）。

## 設計決策（來自 brainstorming）
| # | 決策 | 選擇 |
|---|------|------|
| update 自動化 | 是否自動 pi update | 全自動：git pull + restore + pi update --all（pi 未裝跳過） |
| 觸發 | 一般使用者入口 | 雙軌：選單 `[4] 更新` + 雙擊 `update.bat`/`update.sh` |
| purge 範圍 | 完整刪除 | 全清白，逐項 y/N（`~/.camofox`、`agent.backup.*`、npm uninstall pi），最後提示手動刪 repo |

## 架構與元件

### A. `scripts/setup.py` — `--mode update`
- `--mode` 的 `choices` 由 `["full","model","restore"]` 改為 `["full","model","restore","update"]`。
- `show_main_menu()`：選項列改為 `[1] 完整安裝 [2] 切換模型 [3] 僅還原配置 [4] 更新 [Q] 離開`；輸入 `4` 回傳 `"update"`。
- 新函式 `run_update()`：
  1. `run_stream("git pull --recurse-submodules")`（`run_stream` 預設 `cwd=REPO_ROOT`）。
  2. `run_stream(f'"{sys.executable}" "{restore_script}" --auto')`（restore 預設 profile=standard；冪等、保留使用者自訂）。
  3. `if has_command("pi"): run_stream("pi update --all")`，否則 `print` 略過提示。
- `main()`：`git config --global --add safe.directory` 已對所有 mode 執行；在 mode 分派處，`update` 時呼叫 `run_update()` 後直接結束（不進模型/ profile 流程）。
- 註記（記於 spec + 程式註解）：profile 未持久化，update 以 restore 預設 standard 重新同步；minimal 安裝者更新後會取得 standard 技能集（可接受）。

### B. 雙擊入口
- `update.bat`（新增，Windows CMD，**不需提權**）：
  - `chcp 65001`、確認 python 存在、`python "%~dp0scripts\setup.py" --mode update`、`pause`。
- `update.sh`（新增，POSIX）：`python3 "$SCRIPT_DIR/scripts/setup.py" --mode update`。

### C. `scripts/uninstall.py` — `--purge`
- 引入 `argparse`：`--purge`（store_true）。**不帶 `--purge` 時行為與現況完全一致**。
- 新增 `ask(prompt, default="n")` helper：`--auto`/非 tty 回傳預設（破壞性項預設 `n`），避免 `input()` EOF。
- 修正既有 bug：「Remove Pi」提示的 npm 指令由 `@mariozechner/pi-coding-agent` 改為 `@earendil-works/pi-coding-agent`。
- `--purge` 於正常移除完成後，逐項單獨確認（預設 N）：
  1. `ask("刪除 ~/.camofox（登入 profile/cookies + Camoufox 快取）? [y/N]: ")` → 是則 `remove_path(os.path.expanduser("~/.camofox"))`。
  2. `ask("刪除 restore 備份 ~/.pi/agent.backup.*? [y/N]: ")` → 是則 glob 刪除所有 `~/.pi/agent.backup.*`。
  3. `ask("執行 npm uninstall -g @earendil-works/pi-coding-agent? [y/N]: ")` → 是則實際執行該指令（`subprocess`），否則印出供手動執行。
  4. 最後印：`請手動刪除 repo 資料夾：<REPO_ROOT>`（`REPO_ROOT` = uninstall.py 上溯一層），並提醒 `~/.pi/agent` 已於 restore 時自動備份（若未選刪備份）。

### D. 文檔 `README.md`
- 「更新與升級」段改為：一般使用者雙擊 `update.bat`（macOS/Linux 執行 `bash update.sh`）；進階者 `python scripts/setup.py --mode update`。保留手動三步為備註。
- 新增「解除安裝」小段：`python scripts/uninstall.py`（只移除 harness 管理項）與 `--purge`（完整刪除，逐項確認）。

## 資料流
```
更新：update.bat/sh 或選單[4] → setup.py --mode update
  → git pull --recurse-submodules
  → restore.py --auto  (冪等, 保留使用者自訂 skills/extensions/model 設定)
  → pi update --all    (pi 在才跑; 不在則提示)

完整刪除：uninstall.py --purge
  → (原有) 移除 harness 管理 skills/bridges/rules/AGENTS.md + 清 settings 條目 + PI_HARNESS_ROOT
  → 逐項 y/N(預設N): 刪 ~/.camofox / 刪 agent.backup.* / npm uninstall -g pi
  → 提示手動刪 repo 資料夾
```

## 錯誤處理
- update 任一步 best-effort：git pull 失敗（如本地有改動）印出訊息但續跑 restore；restore 失敗回報；pi update 失敗不影響前兩步成果。
- purge 破壞性項全部 guarded by 確認；非 tty 一律預設不刪，避免自動化誤刪。
- `remove_path` 已 `ignore_errors=True`，缺檔不報錯。

## 測試（`tests/test_update_purge.py`，unittest 零依賴）
- `scripts/setup.py`：字串檢查 `"update"` 在 `--mode` choices、選單含 `[4]`、含 `def run_update`、`run_update` 區塊含 `git pull --recurse-submodules`、`restore` 與 `pi update --all`。
- `update.bat` 存在、含 `--mode update`、含 `chcp 65001`；`update.sh` 存在、含 `--mode update`。
- `scripts/uninstall.py`：含 `argparse`、`--purge`、`.camofox`、`agent.backup`、`@earendil-works/pi-coding-agent`；**不含** `@mariozechner`（scope bug 修掉）；含 `def ask`（非 tty 安全）。
- 平台無關：新出貨檔（update.bat/sh）無機器路徑。
- 語法：`py_compile setup.py uninstall.py`；`sh -n update.sh`。

## 檔案清單
- 改：`scripts/setup.py`（--mode update + 選單 + run_update）、`scripts/uninstall.py`（argparse + --purge + ask + scope 修正）、`README.md`
- 新增：`update.bat`、`update.sh`、`tests/test_update_purge.py`

## 驗證
- `python -m unittest discover -s tests` 全綠（含新測試）。
- `py_compile scripts/setup.py scripts/uninstall.py`；`sh -n update.sh`。
- 沙盒 HOME：`python scripts/setup.py --mode update --auto` 非互動完成（git pull 可能 up-to-date）。
- `python scripts/uninstall.py --purge`（沙盒 HOME，模擬答 N）確認預設不刪 camofox/backups/pi。
- `grep -rn "@mariozechner" scripts/uninstall.py` 無命中。
