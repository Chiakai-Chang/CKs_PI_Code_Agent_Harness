# oh-my-pi 學習復盤：核心收穫與適用性評估

> 綜合 `01-hashline-edit-system` 至 `07-architecture-comparison` 的復盤。

## 最高價值收穫（可直接改善本專案）

### 1. Bridge 健康度驗證（來源：hashline 快照 + natives loader）
oh-my-pi 的 extension loader 有版本 sentinel 和載入診斷；我們的 bridge 註冊是盲信任路徑列表。
**適用性**：高 — 可實作 `bridge-manifest.json`，記錄每個 bridge 的關鍵檔案雜湊 + 版本，啟動時驗證完整性。

### 2. Skill 衝突明確化（來源：skill 發現管道）
oh-my-pi 的提供者優先序 + 名稱去重消除了「同名 skill 誰贏」的模糊性。
**適用性**：高 — `skill-namespace-guard` bridge 正是為此而生，但可升級為正式的名稱衝突檢測 + 報告機制。

### 3. 設定檔安全（來源：hashline 錨定 + 記憶脫敏）
oh-my-pi 的寫入前驗證和脫敏意識，對比我們 `settings.json` 含硬編碼 Windows 路徑且無 schema。
**適用性**：高 — `setup.py` 應引入設定 schema 驗證 + 機器特定值的注入而非模板硬編碼。

### 4. Skill 按需激活（來源：rulebook globs + skill frontmatter）
oh-my-pi 的 `alwaysApply: false` + `globs` 讓技能按需可見，減少情境噪音。
**適用性**：中 — Pi 技能系統支援前導 meta 但本 harness 未充分利用；可為 `chrome-cdp`、`camofox-stealth` 引入條件激活。

### 5. 外部模組統一生命週期（來源：plugin manager + discovery providers）
我們混用 submodule/clone/bridge 蒸餾，無統一管理。oh-my-pi 的 plugin manager + 提供者註冊是更清晰的模型。
**適用性**：中 — 可引入 `external-manifest.json` 統一記錄外部來源、更新策略、依賴關係。

## 中長期概念借鑑（不直接實作但影響設計決策）

- **信任等級框架**（記憶注入）：任何 harness 注入的指令都應標明「啟發性」vs「權威性」
- **租約防多重執行**（記憶整合）：`setup.py --mode restore` 等多終端場景適用
- **軟提醒哲學**（resolve tool）：harness 的指導應引導而非強制
- **主動失效信號**（fs_cache）：設定變更後應有明確狀態信號

## 不適用的設計（明確排除）

- hashline patch language、Rust N-API addon、JSONL session store、bash interceptor — 均為 agent 平台層職責，非 harness 範圍
- snapcompact bitmap 壓縮 — 與 harness 無關

## 適用性總結

| 收穫 | 適用性 | 緊急度 | 實作難度 |
|---|---:|---:|---:|
| Bridge 健康度驗證 | 高 | 高 | 低 |
| Skill 衝突明確化 | 高 | 中 | 低 |
| 設定檔安全與 schema | 高 | 高 | 中 |
| Skill 按需激活 | 中 | 低 | 中 |
| 外部模組統一管理 | 中 | 中 | 高 |
| 信任等級框架 | 概念 | — | — |
| 租約/軟提醒/主動失效 | 概念 | — | — |
