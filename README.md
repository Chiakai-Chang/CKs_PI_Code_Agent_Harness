# CK's Pi Code Agent Harness

> [!NOTE]
> 本專案為 [Pi Coding Agent (pi-mono)](https://github.com/badlogic/pi-mono) 提供通用的配置增強與外部模組管理。透過 Git Submodule 與橋接機制，為本地 AI 代理人建立明確的**行為約束**、**記憶管理**與**安全防禦**。

---

### 🛡️ 開源信任保證 (Trust & License)
*   **100% 乾淨透明**：無任何封閉二進位檔案，所有配置與腳本完全公開。
*   **MIT 授權許可**：本專案採用 MIT 授權，保障使用者之使用、修改與散布權益。

---

## 🚀 快速上手 (Quick Start)

### 1. 取得專案
```bash
git clone --recursive https://github.com/Chiakai-Chang/CKs_PI_Code_Agent_Harness.git
cd CKs_PI_Code_Agent_Harness
```

### 2. 部署配置
*   **Windows**: 雙擊或執行 `install.bat`
*   **macOS / Linux**: 執行 `bash install.sh`

### 3. 更新與升級 (Update)
已安裝過的使用者一鍵更新（設定與自訂技能都會保留）：
*   **Windows**：雙擊 `update.bat`
*   **macOS / Linux**：執行 `bash update.sh`
*   **進階（等同上述）**：`python scripts/setup.py --mode update`
    — 內部自動執行 `git pull --recurse-submodules` → `restore --auto` → `pi update --all`。

> 啟動時若見到 `[Skill conflicts]` 警告：`external/*` 子模組技能（如 `agents-best-practices`、`darwin-skill`）不再於 `restore.py` 執行當下寫死進 `settings.json`。改由 `skill-namespace-guard` 這個 extension 在**每次** Pi 啟動時即時比對——內容跟全域已安裝的版本相同就跳過（不重複註冊），內容不同（你自己另外裝了同名但不同的東西）才會把 harness 這份隔離成 `harness-<name>` 兩份並存，不會動到你自己裝的版本。詳見 [docs/superpowers/specs/2026-07-21-skill-namespace-isolation-design.md](docs/superpowers/specs/2026-07-21-skill-namespace-isolation-design.md)。

### 解除安裝 (Uninstall)
*   **只移除 harness 管理項**（保留你自己的技能與 `~/.camofox` 登入資料）：`python scripts/uninstall.py`
*   **完整刪除、重來**（逐項確認，可額外刪 `~/.camofox`、備份、Pi 本體）：`python scripts/uninstall.py --purge`
    — 最後會提示手動刪除 repo 資料夾。

### 健康度驗證 (Health Checks)
*   **Bridge 驗證**：`python scripts/verify-bridges.py` — 檢查所有橋接程式的入口路徑存在性、manifest 與 package.json 註冊一致性（零依賴）。
*   **設定檔驗證**：`python scripts/validate-config.py` — 檢查 `pi-config/settings.json` 格式完整性、反模式偵測（已提交之機器特定路徑、明文金鑰）。

### 外部來源管理
*   `external-manifest.json` 統一記錄全部外部來源（17 個 Git Submodule、參考克隆、蒸餾來源），取代過去 submodule / clone / 蒸餾混用無統一紀錄的狀態。每個來源標明整合方式（bridge / skill bridge / 僅參考）與更新策略。

### 4. 模式選擇 (Profiles)
安裝時可依需求選擇以下配置模式：
*   **`minimal`** (極簡核心)：適合對對話 Token 敏感的輕量開發。
    *   📦 **僅載入**：`Core 核心`（含 `hello-reflect` 自我演進）、`Caveman`（極簡對話防護）、`ECC`（通用工程實踐）。
*   **`standard`** (預設標準版)：適合日常通用軟體開發。
    *   📦 **載入項目**：包含本專案整合之**所有 17 個外部子模組**與所有本地擴充（TDD 方法論、Wiki 知識庫、AST 圖譜導航等）。
---

---

## 🛠️ 核心功能與 5 層 Harness OS 架構

本專案將 **13 大開源蒸餾核心技能**、**9 大 Extension Bridges** 與 **17 個外部子模組** 無縫熔鑄為 5 層閉環操作系統 (Harness OS)，兼顧開發效率、網頁檢索能力與系統安全：

```
+-----------------------------------------------------------------------+
|  Layer 0: Security & Protection (安全治理與防護層)                     |
|  • YES.md pre-bash-guard (硬擋 rm -rf /、git push --force 等毀滅指令)  |
|  • skill-namespace-guard (動態碰撞隔離) + validate-config.py 靜態合規  |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|  Layer 1: Socratic Framing (需求研討與對立審查層)                       |
|  • grilling-protocol (蘇格拉底一問一答需求釐清門控)                       |
|  • contrarian-review & adversary-review (逆向鋼鐵人反方與極限對立審查) |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|  Layer 2: Context Engine (上下文與記憶專注層)                          |
|  • minimal-prompt-guide (~80-200 Token 注意力專注)                      |
|  • compact-continuation-bridge (對話壓縮後自動接續工作)                |
|  • hello-reflect (經驗自動提煉與 AGENTS.md / CLAUDE.md 規則自演進)     |
|  • Caveman (語意無損 Token 壓縮防禦)                                  |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|  Layer 3: Execution & Repair OS (執行管束、網頁檢索與工具自癒層)        |
|  • browser-automation-guide + camofox-stealth (AX-Tree 定位/反偵測檢索) |
|  • workflow-os-guide (Pins, Gates, Steers & HANDOFF.md 斷點保存)       |
|  • subagent-orchestration-guide (cheap/balanced/max 模型分層調度)     |
|  • tool-repair-guide (9 大 Canonical 欄位自癒修復)                      |
|  • ide-intelligence-guide (LSP 語意診斷前檢 & 模型專屬 Edit 格式)       |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|  Layer 4: Evidence Gate (證據驗證與基因進化層)                        |
|  • autonomous-experiment-guide (MAD 統計顯著性驗證)                    |
|  • harness-factory-guide (Repo Fit 打分、Darwin 演化 & mcp-scan)        |
|  • 173 個自動化單元測試網 (含 TestManagedSkillsConsistency 一致性校驗) |
+-----------------------------------------------------------------------+
```

### 核心功能三大維度與蒸餾技能整合

#### 1. 🌐 網頁檢索與自動化實務 (Web Research & Automation)
*   **隱身網頁瀏覽與搜尋 (`camofox-stealth` + `stealth-web-bridge`)**：內建 Camoufox 反偵測瀏覽器，提供 `web_search` 與 `web_open` 工具，可穿透 Cloudflare 與複雜 JS 牆，支援分頁與登入態管理。
*   **AX-Tree 語意定位 (`browser-automation-guide`)**：蒸餾自 `pi-browser-harness`，優先使用 Accessibility Tree (AX-Tree) 語意節點進行頁面元素定位與變更驗證，大幅提升網頁資料抓取與操作精準度。

#### 2. 🛡️ 安全治理與工程紀律 (Security & Engineering Discipline)
*   **毀滅指令硬封鎖 (`yes-hooks-bridge` / `pre-bash-guard`)**：在模型執行 Bash 前以腳本硬性攔截高風險指令 (`rm -rf /`、`git push --force` 等)。
*   **需求研討與對立審查 (`grilling-protocol` / `contrarian` / `adversary`)**：強制執行一問一答需求釐清，並透過鋼鐵人反方與極限對立測試，避免 AI 瞎猜或陷入單一視角。
*   **工具參數自癒修復 (`tool-repair-guide`)**：提供 9 大 Canonical 欄位修復與降級備援，防止 LLM 工具呼叫時 JSON 格式毀損造成執行中斷。

#### 3. 🧠 工作流與上下文演進 (Workflow & Context Evolution)
*   **模型專屬 IDE 診斷 (`ide-intelligence-guide`)**：自動匹配 LLM 最強 Editing 格式（Line-diff / Full-file / Search-replace），並於儲存前前置觸發 LSP 語意診斷。
*   **斷點保存與續作 (`workflow-os-guide` / `compact-continuation-bridge`)**：產生決定性 `HANDOFF.md` 狀態快照，且在 Context 壓縮時自動續接任務。
*   **海馬迴規則自演進 (`hello-reflect`)**：從每次對話自動提煉經驗，寫入 `.agents/AGENTS.md` / `CLAUDE.md` 實現規則自我進化。

---

## 🎓 13 大蒸餾核心技能 (Distilled Core Skills in `pi-skills/core/`)

本 Harness 將 13 個頂級開源 Agent 專案之精神與演算法精華，蒸餾為零外部依賴、完全遵循 C.A.S.E. 協定的特化技能（收錄於 [pi-skills/core/](file:///D:/MyProject/CKs_PI_Code_Agent_Harness/pi-skills/core/)）：

| 技能名稱 | 蒸餾來源專案 | 核心機制與解決問題 | 整合層級 |
| :--- | :--- | :--- | :---: |
| **`browser-automation-guide`** | [pi-browser-harness](https://github.com/amankumarsingh77/pi-browser-harness) | AX-Tree 語意定位與頁面變更驗證 (配合 `camofox-stealth` 網頁檢索) | Layer 3 |
| **`ide-intelligence-guide`** | [oh-my-pi](https://github.com/audreyt/oh-my-pi) / [can1357](https://github.com/can1357/oh-my-pi) | 模型專屬編輯格式適配 (Model-adapted Edits) 與 LSP 語意診斷前檢 | Layer 3 |
| **`harness-factory-guide`** | [metaharness](https://github.com/ruvnet/metaharness) | Repo Fit 打分 (`score`)、Darwin 演化 (`evolve`) 與 MCP 靜態安全預檢 | Layer 4 |
| **`grilling-protocol`** | [harness-engineering](https://github.com/vinicius91carvalho/harness-engineering) | 一問一答需求研討 (Grilling Interview) 與不可變 Evidence QA 門控 | Layer 1 |
| **`contrarian-review`** | [the-last-harness](https://github.com/diegopetrucci/the-last-harness) | 逆向鋼鐵人反方論證 (Ironclad Anti-Thesis Review) + 28 天自動輪替清理 | Layer 1 |
| **`adversary-review`** | [ultimate-pi](https://github.com/aryaniyaps/ultimate-pi) | 對立面審查與極限壓力測試 (Adversarial Stress Testing) | Layer 1 |
| **`autonomous-experiment-guide`**|[pi-autoresearch-harness](https://github.com/monotykamary/pi-autoresearch-harness)| MAD 統計顯著性評分與自動化實驗 (MAD Statistical Confidence) | Layer 4 |
| **`tool-repair-guide`** | [pi-tool-repair-layer](https://github.com/calionauta/pi-tool-repair-layer) | 9 大 Canonical 欄位修復與強韌 Fallbacks (9 Canonical Field Repairs) | Layer 3 |
| **`guardian-pipeline-guide`** | [agentic-harness.pi](https://github.com/Jitsusama/agentic-harness.pi) | 檢測-解析-審查管線合約與生命週期治理 (`detect` -> `parse` -> `review`) | Layer 4 |
| **`subagent-orchestration-guide`**|[pi-superagents](https://github.com/teelicht/pi-superagents) | 抽象模型分層 (`cheap`/`balanced`/`max`) 與血統上下文隔離 | Layer 3 |
| **`minimal-prompt-guide`** | [Huiyu-Pi](https://github.com/huiyu9144/Huiyu-Pi) | ~80-200 Token 極簡 Prompt 注意力專注 (Attention Focus Optimization) | Layer 2 |
| **`workflow-os-guide`** | [auto-pi](https://github.com/romiluz13/auto-pi) | Pins, Gates, Steers 階段門控與決定性 Handoff 生成 (`HANDOFF.md`) | Layer 3 |
| **`hello-reflect`** | [claude-reflect](https://github.com/BayramAnnakov/claude-reflect) | 規則自演進與海馬迴對話記憶提煉 (Automated Rule & Memory Evolution) | Layer 2 |

---

## 📂 整合外部倉庫 (Submodules & Bridges)

說明：「**外部倉庫**」為整套 Git Submodule 或 Bridge 程式碼庫；「**蒸餾技能**」為提煉其精神、模式與核心演算法後，以 C.A.S.E. 規格重構寫入 [pi-skills/core/](file:///D:/MyProject/CKs_PI_Code_Agent_Harness/pi-skills/core/) 的零依賴核心技能。兩者相互呼應、融會貫通：

| 領域 | 來源專案 / 概念 | 導入方式 | 核心功能 | Minimal | Standard |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **工程紀律** | [ECC](https://github.com/affaan-m/ECC) | Git Submodule | 安全審查與品質門檻 | ⚠️ | ✅ |
| **工作流** | [Planning-with-Files](https://github.com/OthmanAdi/planning-with-files) | Git Submodule | 任務規劃與狀態快照 | ❌ | ✅ |
| **專案知識** | [LLM Wiki](https://github.com/praneybehl/llm-wiki-plugin) | Git Submodule | 知識庫沉澱與鏈接文件 | ❌ | ✅ |
| **方法論** | [Superpowers](https://github.com/obra/superpowers) | Git Submodule | TDD 方法論與微步提交 | ❌ | ✅ |
| **資源防禦** | [Caveman](https://github.com/JuliusBrussee/caveman) | Git Submodule | Token 壓縮防禦 | ⚠️ | ✅ |
| **行為準則** | [Karpathy](https://github.com/multica-ai/andrej-karpathy-skills) | Git Submodule | LLM 寫入防護指引 | ❌ | ✅ |
| **提示工程** | [Prompt Master](https://github.com/nidhinjs/prompt-master) | Git Submodule | 提示詞優化範本 | ❌ | ✅ |
| **安全治理** | [YES.md](https://github.com/sstklen/yes.md) | Submodule + Bridge | `yes` 行為紀律技能＋ `pre-bash-guard` 硬擋毀滅性指令 | ❌ | ✅ |
| **美學/UX** | [Taste Engine](https://github.com/Leonxlnx/taste-skill) | Git Submodule | 設計樣式與視覺引導 | ❌ | ✅ |
| **基因優化** | [Evolver](https://github.com/EvoMap/evolver) | Git Submodule | 失敗模式與 Prompt 演化 | ❌ | ✅ |
| **提示微調** | [Darwin](https://github.alchaincyf/darwin-skill) | Bridge (橋接) | Prompt 變異優化 | ❌ | ✅ |
| **辯證分析** | [Qiushi](https://github.com/HughYau/qiushi-skill) | Bridge (橋接) | 重構前後對照分析 | ❌ | ✅ |
| **除錯實踐** | [Best Practices](https://github.com/DenisSergeevitch/agents-best-practices) | Bridge (橋接) | 系統化除錯引導 | ❌ | ✅ |
| **圖譜導航** | [Graphify](https://github.com/safishamsi/graphify) | Bridge (橋接) | AST 本地圖譜分析 | ❌ | ✅ |
| **循環工程** | [Loopy](https://github.com/Forward-Future/loopy) | Bridge (橋接) | 工作流閉環控制 | ❌ | ✅ |
| **環境治理** | [C.A.S.E.](https://github.com/Chiakai-Chang/Local-Agent-Workspace/tree/main/C.A.S.E._Framework) | Bridge (橋接) | C.A.S.E. 任務管束協定 | ❌ | ✅ |
| **多維推理** | [MECE-Autopilot](https://github.com/Chiakai-Chang/MECE-Autopilot) | Bridge (橋接) | 互斥窮盡多角色辯論與收斂 | ❌ | ✅ |
| **記憶進化** | [claude-reflect](https://github.com/BayramAnnakov/claude-reflect) | 本地移植 (蒸餾) | 專案規則檔案自演進 (`hello-reflect`) | ✅ | ✅ |
| **隱身瀏覽** | [camofox-browser](https://github.com/jo-inc/camofox-browser) | Thin Bridge (橋接) | Camoufox 隱身瀏覽引擎 (`web_*` / `camofox-stealth`) | ❌ | ✅ |

---

## 🛡️ 隱私與安全限制

*   **本地優先**：所有代碼分析（如 AST 拓撲）完全於本地運行，不對外洩漏專案結構。
*   **防寫保護**：防禦規則禁止 AI 任意修改或刪除系統關鍵配置（如 `.env` 與設定檔）。
*   **完全透明**：所有防呆 Hooks 與約束規則完全開源且透明。

---

## 🙏 感謝與授權

*   本專案採用 **MIT 授權**。
*   致謝所有被整合倉庫的作者與貢獻者。詳細決策脈絡請參閱各模組目錄下的 `RATIONALE.md`。

---
**由 [CK (Chiakai Chang)](https://github.com/Chiakai-Chang) 維護。本專案純屬實驗性質。**


