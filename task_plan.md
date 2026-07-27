# 📋 C.A.S.E. / OmniHeal Task Queue & Project Health Check Plan

## 🎯 專案健康檢查目標 (Project Health Check Objectives)
對 `CKs_PI_Code_Agent_Harness` 專案進行徹底的全面健檢與優化，涵蓋：
1. **緊急除錯 (Infinite Loop Fix)**：找出並修復 `pi` 在長時間使用後陷入無限重複 loop 的根因。
2. **OmniHeal 整合與研究隔離**：將 `OmniHeal` 完整載入至 `research/OmniHeal` 並做 `.gitignore` 隔離。
3. **C.A.S.E. 規格化 Tasks Queue**：分階段控管 Context 大小，從小到大、從架構到每個功能間之相依性進行全面審計。
4. **復盤與經驗沉澱**：每個階段 completion 後記錄復盤與脈絡收穫。

---

## 🚦 Task Queue Progress

- [x] **Task 0.1: 根因診斷與緊急修復 (Infinite Loop Fix)**
  - **診斷**: 
    1. `taste-bridge/index.ts` 的 `before_agent_start` 未疊加 `event.systemPrompt`，而是覆蓋覆寫整個 `systemPrompt`，導致底層模型失去原生工具說明與基本 Prompt 指引，轉而印出純文字標籤。
    2. `yes-hooks-bridge/index.ts` 的 `loopGuard` 訊息包含未轉義的 `<invoke>`, `<read-file>`, `<bash>` 標籤，在 LLM 覆述時被再次觸發 `FAKE_TOOL_CALL_PATTERN`。
    3. `loopGuard` 第 3 灰牌（strike 3）原重設次數為 0 且仍送出 `deliverAs: "nextTurn"`，導致 1->2->3->1 無限觸發自回饋循環。
  - **修復**:
    1. 修改 `taste-bridge/index.ts` 讓 `systemPrompt` 正確 append `(event.systemPrompt ?? "")`。
    2. 修改 `yes-hooks-bridge/index.ts` 轉義訊息標籤 `[invoke]`, `[read-file]`, `[bash]`，且第 3 灰牌改為 `deliverAs: "followUp"`（停止自動 `nextTurn` 驅動，等待人類用戶介入）。
    3. 新增 `tests/test_taste_bridge.py` 並補強 `tests/test_yes_hooks_bridge.py` 測試。
  - **驗證**: 176 個 Python 單元測試 100% 通過；`verify-bridges.py` 與 `validate-config.py` 0 失敗。

- [x] **Task 1.1: OmniHeal 複製與研究隔離 (OmniHeal Cloning & Gitignore)**
  - **執行**: Clone `https://github.com/Chiakai-Chang/OmniHeal.git` 到 `research/OmniHeal`，確認 `research/` 已受 `.gitignore` 保護。
  - **驗證**: `research/OmniHeal` 目錄完整性確認 (`README.md`, `LAUNCH.md`, `phases/`, `skills/` 等)。

- [x] **Task 1.2: Layer 0 安全與組態合規健檢 (Security & Protection Audit)**
  - **涵蓋範圍**: `yes-hooks-bridge` (Destructive/Containment/Loop Guard), `skill-namespace-guard` (碰撞隔離與 manifest), `pi-config/` 範本與 `scripts/setup.py` 動態注入。
  - **驗證**:
    1. `yes-hooks-bridge` 包含三大硬性護欄：`bashGuard` (硬擋 `rm -rf /`, `git push --force` 等高風險指令), `containmentGuard` (限制 write/edit 於當前專案 root 避免檔案亂跳), `loopGuard` (3 灰牌機制保護 LLM 免於虛浮標籤循環)。
    2. `skill-namespace-guard` 能動態檢測 `pi-skills/` 與 `external/` 技能命名空間碰撞，並產生 `pi-config/skill-conflict-report.json`。
    3. `validate-config.py` 與 `verify-bridges.py` 驗證全數通過，無硬編碼跨平台路徑與 Zombie Configs。

- [x] **Task 2.1: Layer 1 & Layer 2 語意與 Context Engine 健檢 (Socratic & Context Engine Audit)**
  - **涵蓋範圍**: `minimal-prompt-guide`, `compact-continuation-bridge`, `hello-reflect` 記憶自我演進機制, `grilling-protocol`。
  - **驗證**:
    1. `compact-continuation-bridge` 於 `session_compact` 後會對非 overflow 壓縮觸發接續 Prompt（含 verbatim-preservation 區塊標頭），防止 AI 在 Context 壓縮後中斷失憶。
    2. `hello-reflect` 在 `turn_end` 時可自我探測 Session JSONL 日志並提醒使用者更新 `.agents/AGENTS.md`。

- [x] **Task 3.1: Layer 3 & Layer 4 執行與證據門控健檢 (Execution & Evidence Gate Audit)**
  - **涵蓋範圍**: `stealth-web-bridge`, `planning-with-files-bridge`, `mece-autopilot-bridge`, `autonomous-experiment-guide`, `harness-factory-guide` 以及單元測試完整涵蓋度。
  - **驗證**: 全套 176 個 Python 自動化單元測試 100% 通過（`python -m unittest discover -s tests`）。

- [x] **Task 3.2: 最終綜合健檢報告與 Action Plan 產出 (OmniHeal Summary & Action Plan)**
  - **產出**: 於本專案根目錄下產出 `summary.md`（健檢快照）與 `action_plan.md`（行動路線圖）。

---

## 📝 復盤與脈絡紀錄 (Context & Learnings Log)

### Task 0.1 復盤:
- **疏漏與不當**: 過去在新增 `taste-bridge` 時，沒有撰寫獨立的 `test_taste_bridge.py` 契約測試，導致 `before_agent_start` 直接替換 `systemPrompt` 的致命錯誤未被 CI 抓到。
- **可優化之處**: 所有新增或修改的 Bridge Extensions，都必須在 `tests/` 中編寫對應的 Contract Test，斷言 `(event.systemPrompt ?? "")` 的疊加邏輯。
- **收穫**: 深入理解了 Pi Extension Event System (`before_agent_start`, `turn_end`, `session_compact`) 與 `sendMessage` 的 `deliverAs: "nextTurn"` / `"followUp"` 觸發行為。
