# oh-my-pi 學習筆記：架構對比與本專案差距分析

> oh-my-pi 是完整 coding agent 平台；本專案是 Pi harness 增強框架。兩者定位不同，但 oh-my-pi 的內部設計決策對 harness 層有直接啟發。

## 定位差異

| 維度 | oh-my-pi | 本專案（CK's Harness） |
|---|---|---|
| 定位 | 完整 AI coding agent（terminal-first） | Pi Coding Agent 的配置增強與外部模組管理 |
| 規模 | ~125k LOC（87% TS, 6% Python, 5% Rust） | 數千行（TS bridge + Python setup + Markdown skill/rule） |
| 編輯器 | 自研 hashline patch language | 依賴 Pi 內建 `edit` 工具 |
| 原生層 | ~55k Rust N-API addon | 無原生層 |
| 分發 | npm 套件 + 平台 leaf binary | Git repo + submodule + clone |

## 本專案的結構現狀

- **pi-extensions/**: 9 個 bridge（TypeScript），透過 `settings.json` 註冊為 Pi extension
- **pi-skills/**: 5 個 skill 群組（core/chrome-cdp/dev-browser/graphify/optional），Pi 技能格式
- **pi-rules/**: AGENTS.md + 12 份規則檔案，Pi 規則系統
- **scripts/**: setup.py / restore.py — 互動式設定與還原（Python）
- **external/**: 外部參考克隆（gitignored）

## 關鍵差距

### 1. Bridge 註冊無驗證
oh-my-pi 的 extension loader 有明確的工廠函數契約（default export factory）、版本 sentinel、載入失敗診斷。我們的 bridge 僅是 `settings.json` 中的路徑列表 — 路徑不存在、匯出錯誤、版本不匹配時，失敗模式不明確。

### 2. Skill 發現無衝突解析
oh-my-pi 有提供者優先序 + 名稱去重 + managed fallback 層級。我們的 skill 靠 Pi 內建發現，但 `pi-skills/` 的遞迴結構（`core/`、`optional/`）與 oh-my-pi 的非遞迴設計不同，衝突時行為未定義。

### 3. 設定檔管理脆弱
oh-my-pi 的設定有 schema 驗證、環境變數覆蓋層級、寫入前脫敏。我們的 `settings.json` 含機器特定路徑（`shellPath: C:\Program Files\Git...`）且無 schema，`setup.py` 覆寫時無錨定確認。

### 4. 記憶/壓縮支援薄弱
oh-my-pi 有自主記憶管道和帶邊界保留的壓縮。我們的 `compact-continuation-bridge` 和 `hello-reflect` skill 是輕量嘗試，缺少信任等級框架和失效防護。

### 5. 外部模組管理分散
oh-my-pi 用 plugin manager + 統一發現提供者管理外部能力。我們混用 Git submodule、gitignored clone（`reference/`）、bridge 蒸餾 — 缺乏統一的管理生命週期。

## oh-my-pi 不適用的設計

- **hashline 編輯語言**：我們依賴 Pi 的 `edit` 工具，無法替換其 patch language
- **Rust N-API addon**：harness 層不需原生效能；Pi 平台負責此層
- **完整會話管理**：JSONL session store、session tree 是 agent 核心功能，非 harness 職責
- **bash interceptor**：Pi 的 bash 執行由平台控制，harness 只能透過 hook/bridge 影響
