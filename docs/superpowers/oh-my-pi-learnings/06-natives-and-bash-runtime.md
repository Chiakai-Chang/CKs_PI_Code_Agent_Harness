# oh-my-pi 學習筆記：Natives 原生架構與 Bash 工具運行時

> 來源：`reference/oh-my-pi/docs/natives-architecture.md`、`docs/fs-scan-cache-architecture.md`、`docs/tools/bash.md`、`crates/pi-natives/src/*`

## Natives 原生架構

`@oh-my-pi/pi-natives` 是兩層封裝：ESM loader 包裹 Rust N-API addon，~55,000 行 Rust。

### 二進位分發模型
- 核心套件（npm 發布）**不含** `.node` 二進位，只含 loader 層
- 每個平台標籤（`linux-x64`、`darwin-arm64`、`win32-x64` 等）作為獨立 optional-dependency leaf 套件 `@oh-my-pi/pi-natives-<platform>` 發布
- x64 支援 CPU variant：modern（AVX2）/ baseline（回退），運行時偵測 + `PI_NATIVE_VARIANT` 覆蓋
- 嵌入 addon manifest：gzip tar 歸檔，首次載入時解壓到版本化快取目錄

### 共享 FS Scan Cache
`fs_cache.rs` 實作的全目錄掃描條目快取，被 glob/fuzzyFind/grep/astGrep 共用：
- **快取鍵**：root + include_hidden + use_gitignore + skip_node_modules + detail level — 任一標誌改變即不同分區
- **TTL 策略**：預設 1000ms，環境變數可覆蓋；空結果有獨立更短的重檢時間（200ms）
- **失效機制**：寫入工具呼叫 `invalidateFsScanCache(path)` 主動失效

### Workspace 單趟掃描
`workspace.rs` 的 `listWorkspace`：一次行走同時返回工作區樹條目 + 各目錄的 AGENTS.md 檔案。AGENTS.md 在每個遍歷目錄直接檢查（gitignore 無法隱藏它），排除目錄清單硬編碼在 Rust 層（node_modules、.git、dist、build 等）。

## Bash 工具運行時

- **嵌入式 bash**：vendored brush-shell，持久化 session，超時/中止支援
- **Interceptor**：`bash-interceptor.ts` 擋住危險模式（如 `rm -rf`），可透過設定規則自訂
- **Command Fixup**：自動剝離安全的尾端 `| head`/`| tail` pipe 和冗餘 `2>&1`（native `pi_shell::fixup`）
- **Auto-background**：超過閾值的命令自動轉為背景 job，有 running-job 上限
- **PTY 支援**：互動式命令可走 PTY 路徑，xterm-backed console UI

## 對本專案的啟發

### 直接可用
- **共享快取概念**：我們的 `dev-browser` skill 和 camofox stealth skill 各自獨立啟動瀏覽器/引擎。可引入共享狀態管理 — camofox 引擎下載後全域可用，dev-browser 的 Chrome 連線狀態跨 skill 共享。
- **Interceptor 模式**：oh-my-pi 用 interceptor 擋危險 bash 命令。我們的 `yes-hooks-bridge` 已有 `pre-bash-guard`，但可借鑑 oh-my-pi 的設定化規則系統，讓防護規則可自訂而非硬編碼。
- **主動失效**：`fs_cache` 的寫入後失效模式值得學習 — 我們 `setup.py` 修改設定檔後，應有明確的「狀態已更新」信號，而非依賴下次啟動重新讀取。

### 概念借鑑
- **版本化二進位快取**：oh-my-pi 的 `<getNativesDir()>/<packageVersion>/...` 模式 — 不同版本的二進位不衝突。我們的 camofox 引擎下載可採用類似策略，支援無縫升級。
- **硬編碼排除清單集中化**：oh-my-pi 把排除目錄清單放在 Rust 層作為單一真相來源。本專案的 `.gitignore`、`setup.py` 的忽略邏輯應對齊同一份清單。

### 改善空間（oh-my-pi 自身）
- fs_cache 的 `follow_links` 不在快取鍵中 — 僅由此區分的呼叫可能共享錯誤的快取條目。
- bash interceptor 預設規則在 `settings-schema.ts` 中，非獨立管理，擴充需改設定模式。
