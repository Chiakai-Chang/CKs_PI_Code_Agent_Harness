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

### 3. 更新與升級 (Update & Fix Guide)
已安裝過的使用者一鍵更新（設定與自訂技能都會保留）：
*   **Windows**：雙擊 `update.bat`
*   **macOS / Linux**：執行 `bash update.sh`
*   **進階（等同上述）**：`python scripts/setup.py --mode update`
    — 內部自動執行 `git pull --recurse-submodules` → `restore --auto` （自動同步全部 13 個 Extension 至 `~/.pi/agent/extensions/`） → `pi update --all`。

> 🛠️ **舊用戶修復指南（若遇到 `@file` 無法讀取、標籤/JSON 假工具呼叫卡死、死鎖停擺、agent 宣告下一步就結束回合、PowerShell 指令在 Windows 上總是失敗）**：
> 1. **執行一鍵更新**：執行上述 `update.bat` 或 `bash update.sh`，同步 Universal Parser 標籤轉譯器與 Self-Healing 擴充。
> 2. **確認 `pi-config/harness-config.json` 減重配置**：若使用本地模型（如 `grm-2.6-plus` / llama.cpp），確保配置包含：
>    ```json
>    {
>      "promptProfile": "slim",
>      "enableTasteBridge": false,
>      "enableCaseBridge": true,
>      "caseBridgeMaxChars": 600,
>      "enablePlanningBridge": true,
>      "planningBridgeMaxChars": 600,
>      "enableUniversalTagTransformer": true,
>      "enableSelfHealingLoopGuard": true,
>      "enableDeepResearch": false,
>      "eccSkillModules": ["workflow-quality", "agentic-patterns", "security", "optimization-workflows"]
>    }
>    ```
> 3. **2026-07-31 新增的四道防護**（一鍵更新即生效，無需額外設定）：
>    * **未兌現意圖守衛**：回合宣告「接下來要做 X」卻沒有任何工具呼叫就結束時，自動要求它真的去做。實測中這個形狀造成 6 個真實任務裡 3 個零產出，而既有守衛全部看不見它（它們找的是「宣稱**已完成**」，語意相反）。
>    * **跨 shell 引號守衛**：Windows 上 Pi 透過 bash 執行指令，`powershell -Command "...$var..."` 的變數會先被 bash 吃掉。現在會擋下並指名替代寫法。
>    * **子代理寫入邊界**：`deep_research` 的子代理曾在純研究任務中修改不相關的原始碼，且母 session 的 log 完全看不到。子代理現在不再持有 `bash`/`edit`/`write`。
>    * **子代理輸出上限**：一個失控子代理的 stdout 曾撐爆 V8 字串上限，**殺死母 Pi 行程**。兩條串流現在都有上限。
>
> 4. **2026-08-04 新增 `async-exec-bridge`（一鍵更新即生效）**：新增 `bg_start` / `bg_status` / `bg_cancel` 三個工具，讓 agent 把長工作丟到背景、就地結束該輪，完成時自動被喚醒續跑（詳見上方功能說明與其中的安全須知）。**舊用戶請注意兩件事**：
>    * 更新後 `~/.pi/agent/extensions/` 會多一個 `async-exec-bridge/` 目錄——Pi 是**依目錄自動探索**的，`settings.json` 不會、也不該多出一筆（重複註冊曾造成工具名稱衝突而讓 Pi 完全無法啟動）。
>    * 專案目錄下會出現 `.pi/async-exec/`（工作記錄與輸出擷取），已加入 `.gitignore`。它是崩潰後對帳的唯一依據，請勿在工作進行中刪除。
>    * 同一次更新也修好了一個既有缺陷：`uninstall.py` 的受管 bridge 名單停在 5 個、而 `restore.py` 已管到 11 個，導致解除安裝會在 `~/.pi/agent/extensions/` **留下 7 個 bridge 繼續被載入**。名單現已補齊為 13 個並由測試鎖住，曾解除安裝過的使用者若發現殘留目錄，可手動刪除或重跑一次 `python scripts/uninstall.py`。
>
> 5. **`deep_research` 自 2026-07-31 起預設關閉**（`enableDeepResearch: false`）。實測同一個問題：它耗時 44 分鐘、四個子代理、零可用產出；直接用 `web_search` + `web_open` 則 8 分鐘給出有具名出處的答案。程式碼與測試都保留，要用時把該旗標改成 `true` 再跑一次更新即可。**舊設定檔沒有這個鍵時視為關閉**，所以升級不會意外開啟它。
>
>    *`eccSkillModules` 控制 ECC 子模組要註冊哪些技能。Pi 會把**每一個**已註冊技能的 name / description / 絕對路徑寫進每一輪的 system prompt，ECC 全量 277 個技能實測為 110,240 字元（約 27,560 tokens）。改為依 ECC 上游 module 分類精選後，實測降為 65 個技能；整體技能區塊由 35,437 tokens 降至 14,202 tokens。需要完整領域包時設為 `"all"`，或自行列出 [`external/ecc/manifests/install-modules.json`](external/ecc/manifests/install-modules.json) 中的 module id。*

> 啟動時若見到 `[Skill conflicts]` 警告：`external/*` 子模組技能（如 `agents-best-practices`、`darwin-skill`）不再於 `restore.py` 執行當下寫死進 `settings.json`。改由 `skill-namespace-guard` 這個 extension 在**每次** Pi 啟動時即時比對——內容跟全域已安裝的版本相同就跳過（不重複註冊），內容不同（你自己另外裝了同名但不同的東西）才會把 harness 這份隔離成 `harness-<name>` 兩份並存，不會動到你自己裝的版本。詳見 [docs/superpowers/specs/2026-07-21-skill-namespace-isolation-design.md](docs/superpowers/specs/2026-07-21-skill-namespace-isolation-design.md)。

### 解除安裝 (Uninstall)
*   **只移除 harness 管理項**（保留你自己的技能與 `~/.camofox` 登入資料）：`python scripts/uninstall.py`
*   **完整刪除、重來**（逐項確認，可額外刪 `~/.camofox`、備份、Pi 本體）：`python scripts/uninstall.py --purge`
    — 最後會提示手動刪除 repo 資料夾。

### 健康度驗證 (Health Checks)
*   **Bridge 驗證**：`python scripts/verify-bridges.py` — 檢查所有橋接程式的入口路徑存在性、manifest 與 package.json 註冊一致性（零依賴）。
*   **設定檔驗證**：`python scripts/validate-config.py` — 檢查 `pi-config/settings.json` 格式完整性、反模式偵測（已提交之機器特定路徑、明文金鑰）。
*   **提示衝突稽核**：`python scripts/check-prompt-conflicts.py` — 把 13 個 bridge 各自注入的指令**合起來看**：偵測「for any task」這類無條件宣稱（會吃掉其他工具的適用範圍）、列出被多個工具同時宣稱的觸發詞、統計每輪注入總量，並明確標出它**沒有**涵蓋的部分（直接改寫 `systemPrompt` 的 bridge）。
*   **觸發率量測**：`python scripts/measure-triggers.py` — 以**不點名工具/技能**的情境描述任務，量測該觸發的機制有沒有真的觸發，並含「不該觸發」的反向情境（避免把指引寫得越來越強勢）。每情境重複 N 次取比率（本機模型 temp 0.6，單次樣本不可判讀），session 寫入隔離暫存目錄、cwd 為中性空目錄，避免污染真實歷史。速度慢，**不進 CI**。

### 外部來源管理
*   `external-manifest.json` 統一記錄全部外部來源（18 個 Git Submodule、參考克隆、蒸餾來源），取代過去 submodule / clone / 蒸餾混用無統一紀錄的狀態。每個來源標明整合方式（bridge / skill bridge / 僅參考）與更新策略。

### 4. 模式選擇 (Profiles)
安裝時可依需求選擇以下配置模式：
*   **`minimal`** (極簡核心)：適合對對話 Token 敏感的輕量開發。
    *   📦 **僅載入**：`Core 核心`（含 `hello-reflect` 自我演進）、`Caveman`（極簡對話防護）、`ECC`（通用工程實踐）。
*   **`standard`** (預設標準版)：適合日常通用軟體開發。
    *   📦 **載入項目**：包含本專案整合之**所有 17 個外部子模組**與所有本地擴充（TDD 方法論、Wiki 知識庫、AST 圖譜導航等）。
---

---

## 🛠️ 核心功能與 5 層 Harness OS 架構

本專案將 **13 大開源蒸餾核心技能**、**13 大 Extension Bridges** 與 **17 個外部子模組** 無縫熔鑄為 5 層閉環操作系統 (Harness OS)，兼顧開發效率、網頁檢索能力與系統安全：

```
+-----------------------------------------------------------------------+
|  Layer 0: Security & Protection (安全治理與防護層)                     |
|  • YES.md pre-bash-guard + yes-hooks-bridge (指令硬鎖/Tag轉義/Strike 3)|
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
|  • 490 個自動化單元測試網 (2026-08-04 實跑，含一致性校驗)             |
+-----------------------------------------------------------------------+
```

### 核心功能三大維度與蒸餾技能整合

#### 1. 🌐 網頁檢索與自動化實務 (Web Research & Automation)
*   **深度網頁研究 (`deep_research` 工具 + `deep-research-guide`)**：不再只是散文指引——`deep-research-bridge` 註冊真正的 `deep_research` 工具，把每個子問題 spawn 成獨立的 `pi --print` 子行程（Pi 官方 subagent 做法）。子行程用自己的 context 讀網頁，只回傳精簡發現。**序列執行、上限 5 個子問題**，因為本機 llama.cpp 以 `-np 1` 啟動時並行請求會序列化（實測：兩個並行請求分別於 7.3s / 14.3s 完成），並行不會更快、只會讓牆鐘時間乘以 N。價值在 **context 隔離**：實測一次研究回傳父層僅 1,408 字元，而父層直接 `web_search` 單次就是 14,613 字元。
*   **隱身網頁瀏覽與搜尋 (`camofox-stealth` + `stealth-web-bridge`)**：內建 Camoufox 反偵測瀏覽器，提供 `web_search` 與 `web_open` 工具，可穿透 Cloudflare 與複雜 JS 牆，支援分頁與登入態管理。實測 126 次搜尋僅 1 次被擋。回傳採**閱讀檢視**：依 AX-tree 語意角色剝除導覽子樹、`/url:` 管線與 `[eN]` 參照（實測文章頁 8,253→1,936 字元、連結密集首頁 34,012→18,954 且 48 個標題連結全保留），並統一套用 Pi 自身的 2000 行 / 50KB 工具輸出預算、超出部分落檔並在結果中告知路徑。需要點擊/輸入時以 `raw: true` 或 `web_snapshot` 取回完整樹。
*   **AX-Tree 語意定位 (`browser-automation-guide`)**：蒸餾自 `pi-browser-harness`，優先使用 Accessibility Tree (AX-Tree) 語意節點進行頁面元素定位與變更驗證，大幅提升網頁資料抓取與操作精準度。

*   **背景執行與自動續跑 (`bg_start` / `bg_status` / `bg_cancel` + `async-exec-bridge`)**：慢模型本身不是最痛的，**慢又同步**才是——工作交出去以後 agent 只能卡著等，人也被綁在螢幕前。`bg_start` 把長工作（build、整套測試、benchmark）以 detached 子行程送出後**立刻回傳**，agent 可以就地結束這一輪；工作完成時 bridge 主動喚醒它並帶回結果尾段，全部做完再以 `agent_settled` 通知你一次。實測（GRM-3.2-Sky-OPAL，Vulkan，`-np 1`）：派工到自動續跑 32 秒，其中工作本身佔 20 秒。狀態一律落檔在 `.pi/async-exec/`，所以 Pi 被砍掉也能在下次啟動時對帳補報。
    *   **安全須知**：`bg_start` 執行的是**任意 shell 指令、detached、不另外確認**，而且**中止 agent 不會中止它派出的背景工作**——這既是它的價值也是它的風險。要停就用 `bg_cancel`（連整棵進程樹一起殺）。目前沒有白名單與確認提示，若要接不受信任的提示來源請先自行加上。
    *   **逐工作逾時**：`bg_start` 可傳 `timeoutMs` 覆寫預設的 30 分鐘,值由機制**夾在 10 秒至 24 小時之間**（模型給的值不被信任;`NaN` 這類輸入會退回預設,否則會變成「永遠不會逾時」）。逾時會殺掉整棵進程樹並標記為 `timeout`。
    *   **Telegram 旁路通知（選用,預設關閉）**：在 `pi-config/harness-config.json` 設 `"asyncExecTelegramNotify": true` 後,全部工作做完時除了終端機通知,也會透過**你已設定好的 `pi-telegram`**（讀 `~/.pi/agent/telegram.json` 的 `botToken` 與 `allowedUserId`）發一則訊息。**預設關閉是刻意的**——這是對外網路傳送,不該因為偵測到設定檔就自動開啟。未安裝／未連線／傳送失敗一律靜默略過,**絕不影響工作狀態**。
    *   **磁碟保留策略（保守預設）**：已回報且已完成的工作紀錄保留 **7 天**，且最多保留 **50 筆**，超出者由舊到新清除（連同輸出擷取檔一起）。**執行中、以及尚未回報過的完成結果永不清除**，不論多舊——那是崩潰復原唯一的依據。清理在 `session_start` 對帳**之後**才進行，所以不會刪掉還沒被讀到的結果。
    *   **`localModel` 參數**：`none`（預設，可重疊）／`shared`（共用同一個本地模型 server）／`exclusive`（v1 直接拒絕——沒有 GPU 探測就無法誠實判斷第二個模型塞不塞得下，寧可拒絕也不猜）。若你的 llama-server 以 `-np 2` 以上啟動，設環境變數 `PI_MODEL_SERVER_SLOTS` 對應該值；預設值 1 是保守讀法，會如實警告 `shared` 工作會**阻塞**而非只是拖慢。

#### 2. 🛡️ 安全治理與工程紀律 (Security & Engineering Discipline)
*   **毀滅指令硬封鎖與循環防禦 (`yes-hooks-bridge` / `pre-bash-guard`)**：在模型執行 Bash 前以腳本硬性攔截高風險指令 (`rm -rf /`、`git push --force` 等)；內建 `loopGuard` 轉義標籤並於 Strike 3 自動啟動人類控制權斷路器（`deliverAs: "followUp"`），防止 Agent 陷入無限重複死循環。

*   **需求研討與對立審查 (`grilling-protocol` / `contrarian` / `adversary`)**：強制執行一問一答需求釐清，並透過鋼鐵人反方與極限對立測試，避免 AI 瞎猜或陷入單一視角。
*   **工具參數自癒修復 (`tool-repair-guide`)**：提供 9 大 Canonical 欄位修復與降級備援，防止 LLM 工具呼叫時 JSON 格式毀損造成執行中斷。

#### 3. 🧠 工作流與上下文演進 (Workflow & Context Evolution)
*   **模型專屬 IDE 診斷 (`ide-intelligence-guide`)**：自動匹配 LLM 最強 Editing 格式（Line-diff / Full-file / Search-replace），並於儲存前前置觸發 LSP 語意診斷。
*   **斷點保存與續作 (`workflow-os-guide` / `compact-continuation-bridge`)**：產生決定性 `HANDOFF.md` 狀態快照，且在 Context 壓縮時自動續接任務。
*   **海馬迴規則自演進 (`hello-reflect`)**：從每次對話自動提煉經驗，寫入 `.agents/AGENTS.md` / `CLAUDE.md` 實現規則自我進化。

---

## ⚙️ Harness OS 與 Pi Engine 整合架構與共存矩陣

本專案與原生 Pi Coding Agent 引擎**並非競爭或重複**，而是作為 **「Pi 引擎的 Harness OS (駕駛艙與守護框架)」**。詳細之完整 MECE 分析請參閱獨立技術文件：[📖 Harness OS 整合與共存完整指南 (docs/core/HARNESS_INTEGRATION_GUIDE.md)](docs/core/HARNESS_INTEGRATION_GUIDE.md)。

### 💡 三大核心共存保證 (Coexistence Promises)

1. **零覆蓋保護 (Zero Overwrite)**：`restore.py` 與 `uninstall.py` 嚴格限定僅管理 `managed_skills` 清單，絕不任意刪除或覆蓋使用者自行安裝於全域的 `.pi/agent/skills/` 與 `extensions`。
2. **動態碰撞隔離 (Namespace Guard)**：當使用者安裝之技能與本專案外部技能同名時，`skill-namespace-guard` 在每次 Pi 啟動時自動比對，若內容不同則平滑重命名為 `harness-<name>` 獨立並存。
3. **零擴充雙重註冊碰撞 (Config Hygiene)**：本 Harness 內部 13 大 Extension Bridges（如 `yes-hooks-bridge`、`stealth-web-bridge` 等）由 `restore.py` 實體複製至擴充目錄並由 Pi 自動載入，**絕不**重複寫入 `settings.json` 的 `extensions` 陣列中，防止 `registerTool()` 工具同名衝突崩潰。

---

## 🎓 蒸餾核心技能 (Distilled Core Skills in `pi-skills/core/`)

本 Harness 將 13 個頂級開源 Agent 專案之精神與演算法精華，蒸餾為零外部依賴、完全遵循 C.A.S.E. 協定的特化技能（收錄於 [pi-skills/core/](file:///D:/MyProject/CKs_PI_Code_Agent_Harness/pi-skills/core/)）：

| 技能名稱 | 蒸餾來源專案 | 核心機制與解決問題 | 整合層級 |
| :--- | :--- | :--- | :---: |
| **`deep-research-guide`** | [pi-browser-harness](https://github.com/amankumarsingh77/pi-browser-harness) | 需求多維拆解、多子代理發散檢索、雙重硬上限門控與具名引用報告生成 | Layer 3 |
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


