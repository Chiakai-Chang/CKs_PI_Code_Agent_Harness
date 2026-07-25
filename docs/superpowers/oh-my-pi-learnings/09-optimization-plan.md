# oh-my-pi 學習後優化計畫

> 基於 `08-review-and-findings` 的適用性評估，聚焦高適用性 + 高/中緊急度項目。

## 工作清單

### A. Bridge 健康度驗證（高適用性 / 高緊急度）
**目標**：消除 bridge 註冊的盲信任 — 路徑不存在、匯出錯誤時有明確診斷。

- [x] A1. 建立 `pi-extensions/bridge-manifest.json`：記錄每個 bridge 的路徑、版本、描述
- [x] A2. 新增 `scripts/verify-bridges.py`：驗證所有註冊 bridge 路徑存在且可匯入，報告缺失
- [ ] A3. 升級 `skill-namespace-guard` bridge：啟動時讀取 manifest 驗證（需 Pi 環境測試）

**oh-my-pi 借鑑點**：natives loader 的載入診斷 + hashline 的內容雜湊驗證哲學。

### B. Skill 衝突檢測與報告（高適用性 / 中緊急度）
**目標**：明確化 skill 名稱衝突時的行為，不再「未定義」。

- [x] B1. 升級 `skill-namespace-guard` bridge：掃描所有 skill 來源（pi-skills/、submodule skills、external skills）的名稱，檢測衝突，寫入報告到 `pi-config/skill-conflict-report.json`
- [ ] B2. 引入提供者優先序概念：在 AGENTS.md 中文件化各 skill 來源的優先級

**oh-my-pi 借鑑點**：skill 發現管道的提供者優先序 + 名稱去重 + managed fallback。

### C. 設定檔安全強化（高適用性 / 高緊急度）
**目標**：`settings.json` 不再含機器特定值，`setup.py` 覆寫前有驗證。

- [x] C1. 從 `settings.json` 移除硬編碼 Windows `shellPath`，改為 `setup.py` 運行時偵測注入
- [x] C2. 新增 `scripts/validate-config.py`：對 pi-config/ 下的設定檔做基本 schema 驗證（路徑存在性、必要欄位）
- [ ] C3. 升級 `restore.py`：覆寫設定前驗證來源完整性

**oh-my-pi 借鑑點**：hashline 的錨定確認哲學 + 記憶輸出的脫敏寫入意識。

### D. 外部模組統一管理（中適用性 / 中緊急度）
**目標**：不再混用 submodule/clone/蒸餾而無統一記錄。

- [x] D1. 建立 `external-manifest.json`：統一記錄所有外部來源（submodule、reference clone、bridge 蒸餾來源）、更新策略、依賴關係
- [ ] D2. 新增 `scripts/update-externals.py`：基於 manifest 更新外部來源

**oh-my-pi 借鑑點**：plugin manager + discovery provider 的統一註冊模型。

## 不實作的項目（明確排除）

- hashline patch language 移植 — agent 平台層職責
- Rust N-API addon — harness 層不需原生層
- 完整壓縮/記憶管道 — Pi 平台已有基礎，harness 只做增強
- snapcompact / session tree — 與 harness 無關

## 驗證策略

遵循本專案 `CLAUDE.md` 的「實測有證據」原則：
- A/B/C 項目的驗證腳本必須實際執行並報告真實結果，不預測不推測
- 不修改 Pi 平台核心行為（edit/bash/session），只增強 harness 自身的健康管理
- 所有新增腳本零依賴（stdlib only），與現有 `setup.py` 一致
