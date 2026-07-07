# Harness 全面審查與修復計畫 (2026-07-07)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 驗證本專案是否落實其自述理念（Anti-Bragging、No Zombie Configs、Platform-Agnostic、bash 相容），修復安裝/設定/切換模型/還原流程中的根因缺陷。

**Architecture:** 不改變整體架構（setup.py 編排 + restore.py 資產還原 + 橋接擴充）。僅修正合併策略、子程序工作目錄、非互動模式與硬編碼路徑，並讓測試零依賴可跑（unittest）且納入 CI。

**Tech Stack:** Python 3 標準庫（零依賴）、Batch/Bash 啟動器、GitHub Actions。

## Global Constraints

- 零依賴原則：腳本僅用 Python 標準庫；測試用 `unittest`（不得引入 pytest 依賴）。
- 平台無關：共享模板/規則檔內嚴禁機器路徑（`D:/...`、`C:\...`）；OS-specific 值由 `setup.py` 執行期注入。
- 文檔連結一律用倉庫相對路徑，不用 `file:///` 絕對連結。
- 不使用行銷用語；文檔描述必須與代碼實際行為一致。

---

## 審計發現（Findings）

### A. 功能性根因缺陷（安裝 / 設定 / 更新）

| # | 位置 | 問題 | 根因 |
|---|------|------|------|
| A1 | `scripts/restore.py` `deep_merge` | 「切換模型」永遠無效：`deep_merge(agent現有設定, pi-config新設定)` 採 target 優先，首次安裝後 `defaultModel/defaultProvider/apiBase` 再也不會被更新；切換到雲端供應商時殘留的 `apiBase` 不會被清除（違反 DISTILLATION_GUIDE 第 8 條） | 合併策略未區分「harness 管理鍵」與「使用者自訂鍵」 |
| A2 | `scripts/setup.py` mode=model | 切換模型會無條件以 `--profile standard` 重跑完整 restore，minimal 用戶被強制升級成 standard 技能集 | profile 未持久化，且 restore 缺少「僅同步配置」模式 |
| A3 | `scripts/setup.py` 環境檢查 | 檢查 `python --version`，macOS/Linux 常僅有 `python3` → 完整安裝直接退出 | 檢查了「正在執行自己」的直譯器，應直接用 `sys.executable` |
| A4 | `scripts/setup.py` `run()/run_stream()` | 未傳 `cwd` → `git submodule update` 等在呼叫者當前目錄執行；經 install.bat 提權後 cwd 是 System32，子模組拉取靜默失敗 | 子程序未綁定 `REPO_ROOT` |
| A5 | `install.bat` 提權 | `Start-Process python -ArgumentList '%~dp0scripts\setup.py'` 路徑未加引號（含空格即壞）、未設 `-WorkingDirectory`、完成即關窗看不到錯誤/結果 | 提權指令三重缺陷 |
| A6 | `scripts/setup.py` `--auto` | `AUTO_MODE` 是死變數；非互動環境（CI、管線）中 `input()` 直接 EOFError。CLAUDE.md 宣稱 `--mode restore` 可「直接還原」實際仍會互動卡住 | 旗標從未接線到任何 prompt |
| A7 | `scripts/uninstall.py` | 直接 `rmtree` 整個 skills/rules/extensions → 把使用者自己的技能一併刪除，與其「不刪個人檔案」宣稱矛盾（restore.py 反而有保留邏輯） | 解除安裝未使用「harness 管理清單」 |
| A8 | `scripts/restore.py:78` | `stat` 未匯入即使用（NameError 被裸 except 吞掉）→ 唯讀 symlink 清理靜默失敗 | 區域性 `import stat` 散落、遺漏一處 |
| A9 | `scripts/restore.py` models.json | 以整檔覆蓋 `~/.pi/agent/models.json`，會抹掉使用者其他自訂 provider | 未做 provider 層級合併 |

### B. 違反自家憲章（DISTILLATION_GUIDE / CLAUDE.md 規則）

| # | 位置 | 問題 |
|---|------|------|
| B1 | `pi-rules/AGENTS.md:11` | 硬編碼 `D:/MyProject/everything-claude-code/agents`——此檔會被複製到**所有使用者**的 `~/.pi/agent/`，直接違反 No OS-Specific Hardcoding |
| B2 | `CLAUDE.md`、`.cursorrules`、`.agents/AGENTS.md`、`docs/core/DISTILLATION_GUIDE.md` | `file:///D:/Myproject/...` 絕對連結（大小寫還與實際 `MyProject` 不符），換機器全數失效 |
| B3 | `pi-config/settings.json.example` | 模板內建 `defaultProvider: ollama / defaultModel: llama3.2 / apiBase / "shellPath": ""`——跳過模型設定的新用戶會被塞入指向不存在服務的預設；模板應供應商/平台中立 |
| B4 | `package.json` `pi` 區段 | 與 restore.py 實際註冊不同步：extensions 缺 `case-bridge`、`taste-bridge`；skills 缺 `pi-skills/graphify`（半殭屍清單） |
| B5 | `README.md` | Karpathy 連結指向 `forrestchang/...`，.gitmodules 實為 `multica-ai/...`（違反 Canonical Links 規則）；minimal 描述說「僅載入 Core+Caveman+ECC」但 restore.py 一律載入 chrome-cdp/dev-browser |
| B6 | `scripts/setup.py` 雲端模型選單 | 過時（claude-3-5-sonnet-latest / claude-3-opus-latest 已退役、gemini-2.0 系列過期），與「實事求是」原則不符 |

### C. 品質 / 可維護性

| # | 位置 | 問題 |
|---|------|------|
| C1 | `tests/test_onboarding.py` | pytest 風格函式，但專案零依賴（pytest 未裝）→ 實際跑不了；CI 只做 lint 不跑任何測試；CLAUDE.md 測試指令空白 |
| C2 | `docs/core/DISTILLATION_GUIDE.md` | 兩個「第五步」編號重複 |
| C3 | `scripts/restore.py` `confirm()` | 訊息說會覆蓋 `config.json`，實際行為是刪除（已廢棄）該檔 |
| C4 | `pi-skills/core/bridges/*`（僅 RATIONALE.md）| 會被整批複製到 `~/.pi/agent/skills/bridges/`，不是合法 skill（無 SKILL.md），屬決策文檔——建議不複製（觀察項，本次不動架構，只跳過複製） |

---

## Task 1: restore.py 合併策略與還原修復

**Files:**
- Modify: `scripts/restore.py`
- Test: `tests/test_restore.py`（新增）

**Interfaces:**
- Produces: `merge_settings(existing, incoming, incoming_is_real)`（供測試匯入）、`merge_models(existing, incoming)`、CLI 旗標 `--config-only`
- Consumes: 無

- [ ] **Step 1: 寫失敗測試** `tests/test_restore.py`（unittest；驗證 harness 管理鍵覆蓋、apiBase 清除、example 回退不覆蓋、models provider 合併）
- [ ] **Step 2: 跑測試確認失敗**：`python -m unittest tests.test_restore -v` → FAIL（函式不存在）
- [ ] **Step 3: 實作**：
  - 頂部 `import stat`，移除散落的區域 import（修 A8）
  - 抽出 `merge_settings()`：先 `deep_merge`（target 優先，保護使用者自訂），再當 `incoming_is_real=True` 時強制以 incoming 的 `defaultModel/defaultProvider/apiBase/shellPath` 覆蓋，且 incoming 沒有 `apiBase` 時從結果刪除（修 A1）
  - 抽出 `merge_models()`：以 provider 名稱為單位 update，保留使用者其他 provider（修 A9）
  - 新增 `--config-only`：僅備份 + 合併 settings + 同步 models.json，不動 skills/rules/extensions 與 profile 註冊（修 A2 的 restore 側）
  - chrome-cdp / dev-browser 移入 standard 分支（對齊 README minimal 描述，修 B5 後半）
  - `confirm()` 訊息改為實際行為（修 C3）
  - 複製 core skills 時跳過 `bridges` 資料夾（C4）
- [ ] **Step 4: 跑測試確認通過** + `python -m py_compile scripts/restore.py`
- [ ] **Step 5: Commit**

## Task 2: setup.py 編排修復

**Files:**
- Modify: `scripts/setup.py`

**Interfaces:**
- Consumes: restore.py 的 `--config-only`
- Produces: `ask(prompt, default)` 非互動輔助函式

- [ ] **Step 1**: `run()/run_stream()` 增加 `cwd=REPO_ROOT` 預設（修 A4）
- [ ] **Step 2**: 環境檢查改為 `["git", "npm"]`（Python 已在執行自身；修 A3）
- [ ] **Step 3**: 新增 `ask()`：`AUTO_MODE` 或非 tty 時回傳預設值並列印；所有 `input()` 改走 `ask()`（修 A6）
- [ ] **Step 4**: mode=model 時以 `--config-only` 呼叫 restore.py；mode=model 不再詢問/套用 profile（修 A2）
- [ ] **Step 5**: 更新雲端模型選單至現行世代（Anthropic: claude-sonnet-4-5 / claude-haiku-4-5 / claude-opus-4-1；Google: gemini-2.5-flash / gemini-2.5-pro；保留自訂輸入）（修 B6）
- [ ] **Step 6**: `python -m py_compile scripts/setup.py` + `python scripts/setup.py --mode restore --auto` 全程無互動完成
- [ ] **Step 7: Commit**

## Task 3: install.bat 提權修復

**Files:**
- Modify: `install.bat`

- [ ] **Step 1**: 提權改為帶引號路徑 + `-WorkingDirectory` + `cmd /k` 保留視窗（修 A5）
- [ ] **Step 2**: 驗證 `tests/test_onboarding` 相關斷言仍通過
- [ ] **Step 3: Commit**

## Task 4: uninstall.py 選擇性移除

**Files:**
- Modify: `scripts/uninstall.py`

- [ ] **Step 1**: 只移除 harness 管理項目：`managed_skills` + optional skills、5 個橋接 extension、rules（rules 目錄由 harness 全量管理可整刪）；並從 `settings.json` 清掉指向 harness repo 的 skills/extensions/prompts 條目與 `PI_HARNESS_ROOT`（修 A7）
- [ ] **Step 2**: `python -m py_compile scripts/uninstall.py`
- [ ] **Step 3: Commit**

## Task 5: 硬編碼與文檔一致性清理

**Files:**
- Modify: `pi-rules/AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.agents/AGENTS.md`, `docs/core/DISTILLATION_GUIDE.md`, `README.md`

- [ ] **Step 1**: `pi-rules/AGENTS.md` 第 2 節改指向 `$PI_HARNESS_ROOT/external/ecc/agents`（環境變數由 restore 注入）（修 B1）
- [ ] **Step 2**: 全部 `file:///D:/Myproject/...` 連結改倉庫相對路徑（修 B2）
- [ ] **Step 3**: README Karpathy 連結改 canonical `multica-ai/andrej-karpathy-skills`（修 B5）
- [ ] **Step 4**: DISTILLATION_GUIDE「第五步」重複編號改為第五步/第六步（修 C2）
- [ ] **Step 5: Commit**

## Task 6: 模板與 pi 清單同步

**Files:**
- Modify: `pi-config/settings.json.example`, `package.json`

- [ ] **Step 1**: example 模板移除 `defaultProvider/defaultModel/apiBase/shellPath`（供應商/平台中立；由 setup.py 執行期寫入真值）（修 B3）
- [ ] **Step 2**: `package.json` `pi.extensions` 補上 `case-bridge`、`taste-bridge`；`pi.skills` 補 `pi-skills/graphify`（修 B4）
- [ ] **Step 3**: CI 的 JSON 驗證通過
- [ ] **Step 4: Commit**

## Task 7: 測試零依賴化與 CI 接線

**Files:**
- Modify: `tests/test_onboarding.py`（轉 unittest）, `.github/workflows/ci.yml`, `CLAUDE.md`

- [ ] **Step 1**: test_onboarding.py 改為 `unittest.TestCase`（修 C1）
- [ ] **Step 2**: CI 增加 `python -m unittest discover -s tests -v`
- [ ] **Step 3**: CLAUDE.md 測試指令填入 `python -m unittest discover -s tests`
- [ ] **Step 4**: 本地全套測試通過
- [ ] **Step 5: Commit**

---

## 驗證

- `python -m unittest discover -s tests -v` 全綠
- `python -m py_compile scripts/setup.py scripts/restore.py scripts/uninstall.py`
- `python scripts/setup.py --mode restore --auto` 非互動完成（實際寫入 `~/.pi/agent`）
- `grep -rn "D:/MyProject\|Myproject" --include="*.md" .`（排除 external/、docs/history、docs/superpowers 歷史計畫）無共享規則檔命中
