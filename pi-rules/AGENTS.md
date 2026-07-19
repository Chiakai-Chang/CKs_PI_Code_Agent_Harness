# Agent Instructions

## 0. Language & Locale (中文回應規範)
When responding in Chinese, ALWAYS use Traditional Chinese with Taiwan-standard terminology (正體中文，臺灣慣用語), never Simplified Chinese. Keep code, commit messages, and identifiers in English as usual.
*   **字形**：一律使用正體字（繁體），嚴禁簡體字。
*   **臺灣慣用術語對照**（遇到下列概念時使用左側用語）：檔案（非「文件」，document 才是文件）、程式碼（非「代码」）、軟體（非「软件」）、資料（非「数据」）、網路（非「网络」）、預設（非「默认」）、品質（非「质量」）、物件導向（非「面向对象」）、變數（非「变量」）、迴圈（非「循环」）、函式（非「函数」）、伺服器（非「服务器」）、記憶體（非「内存」）、硬碟（非「硬盘」）、影片（非「视频」）、專案（非「项目」）、支援（非「支持」，除非指精神上的支持）、最佳化（非「优化」）。
*   **標點**：使用全形標點（，、。；：「」）於中文語句。
Even though the operating system is Windows (e.g., CWD/paths look like `C:/...` or `D:/...`), the underlying shell for the `bash` tool is configured as **Git Bash (bash.exe)**.
*   **Path Formatting**: ALWAYS use forward slashes (`/`) for paths when writing commands or referring to files (e.g., `ls src/core` instead of `ls src\core`).
*   **UNIX Utilities**: ALWAYS use standard UNIX utilities (`ls`, `grep`, `find`, `cp`, `mv`, `rm`, `cat`, `mkdir`, `rmdir`, etc.) in the `bash` tool.
*   **No PowerShell/CMD**: NEVER use PowerShell or CMD commands (e.g., `Get-ChildItem`, `gc`, `dir`, `copy`, `move`, `del`, `type`, `md`, or `%APPDATA%`).
*   **Chaining Commands**: Use `&&`, `||`, and `;` to chain commands instead of PowerShell's `;` or CMD's `&`.

## 2. Agent Orchestration Routing
For complex tasks, delegate to the specialised ECC agent personas bundled with this harness under `$PI_HARNESS_ROOT/external/ecc/agents` (the `PI_HARNESS_ROOT` env var is injected by `scripts/restore.py`):
*   Use `planner` for implementation planning.
*   Use `architect` for system design.
*   Use `tdd-guide` for new features or bug fixes.
*   Use `code-reviewer` after writing code.
*   Use `security-reviewer` before commits.

## 3. CLI Design Standards
Follow compact output rules:
*   Pass `--compact` or `--select` flags where supported to minimize data transfer.
*   Check exit codes for automated retry strategies.

## 4. Self-Correction & Bounded Optimization (SkillOpt & C.A.S.E. Protocol)
To prevent infinite loops and improve success rates during debugging or tool failures:
*   **Rejected Memory**: If a command or test fails, record the failed approach and the exact error output in `.pi/rejected_attempts.json` or `findings.md`.
*   **Bounded Correction**: Before retrying, read the rejected attempts to ensure the new approach does not repeat previous errors. Modify only the specific code or parameters that failed.
*   **3-Strike Cap**: Limit consecutive retries of the same task to 3 attempts. On the 3rd failure, stop, write the failure log to `findings.md`, and escalate to the user with a summary.
*   **C.A.S.E. & Planning-with-Files Nesting**: When C.A.S.E. is active (indicated by `CASE.md` or `00_Constitution`), you MUST nest your `task_plan.md`, `findings.md`, and `progress.md` (from `planning-with-files`) INSIDE your active task directory (e.g. `02_Task_Queue/Task_<NNN>_<slug>/`) rather than the workspace root. Use `status.txt` to manage micro-state transitions (`IN_PROGRESS` -> `REVIEW`).
*   **Loop Engineering (Loopy Protocol)**: When executing or designing repeatable workflows (e.g. docs sync, test expansion, migrations), model them as bounded loops. Define: (1) target objective, (2) verification check, (3) feedback action, and (4) terminal/escalation conditions. Check catalog recommendations before inventing a new loop.
*   **Genetic Gating & PR Isolation (GEPA Protocol)**: When proposing a permanent optimization or modification to an agent skill (e.g., `SKILL.md`), NEVER apply it directly to the active configuration. Instead, create a separate git branch (`evolve/skill-name`), perform sandboxed trials, and present the final version to the user as a Git Diff/PR for explicit review and validation.

## 5. Persistent Knowledge Base & Cognitive Synergy (LLM Wiki & Graphify Protocol)
When accumulating knowledge, research papers, design decisions, or codebase architecture:
*   **Compilation over RAG**: Treat the LLM as a librarian. When a new raw source or reference document is introduced, compile it once into a persistent, interlinked wiki in the `wiki/` directory rather than re-reading raw files repeatedly.
*   **Keep it Atomic**: Ensure all wiki pages remain small (soft cap 400 lines) and are indexed in `wiki/index.md` or sharded indexes under `wiki/indexes/`.
*   **Graph Linking**: Use standard markdown wikilinks `[[page-name]]` to build a semantic knowledge graph. Use frontmatter variables (`type`, `tags`, `sources`, `updated`) on every wiki page.
*   **Code Graph Alignment (Graphify Integration)**: Before answering architecture or codebase questions, check whether `graphify-out/GRAPH_REPORT.md` exists. If so, read it first to navigate god nodes and community structures. If `wiki/index.md` exists alongside the graph, navigate the wiki instead of reading raw files. Run `graphify update .` (AST-only, no API cost) after code changes to keep the graph in sync.

## 6. Collective Skill Evolution (SkillClaw & Darwin Protocol)
When learning from sessions or optimizing local skills/rules:
*   **History ledger priority**: Before editing any existing skill or configuration (e.g. `SKILL.md`), you MUST search for its history records (`history/v*.md` or past commits/rationales). Explicitly document: what changed in each prior version, what evidence drove it, and whether later sessions suggested it helped or hurt.
*   **Summarize & Decide (SkillClaw + Darwin)**: Group session logs/rationales. Use `SkillClaw` to decide macro updates: `create_skill`, `improve_skill`, or `skip`. If a skill's prompts require micro-tuning, trigger `darwin-skill` to execute sandboxed mutation trials.
*   **Rigorous Self-Validation (GEPA + Qiushi Synergy)**: Before finalizing any skill optimization, define 1-3 validation scenarios from session evidence. Run a dry run or static simulation on a separate branch. Use `contradiction-analysis` (qiushi-skill 的辯證方法) to establish a clean control group comparison. Write validation logs to `history/v<N>_evidence.md` before merging via Git Diff.

## 7. Quality & Performance Harmony (UI/UX Pro Max & Addyosmani Protocol)
When implementing frontend designs and components:
*   **Design-Performance Budget**: Before writing CSS/JS under `ui-ux-pro-max`, read the performance budgets defined by `addyosmani-skills`. Ensure animations, gradients, and font imports do not breach LCP/CLS/FID targets.
*   **Automated Validation**: After design completion, run `browser-testing-with-devtools` in headless chrome to verify that aesthetic components do not regress loading speeds. Do not claim UX completion without performance telemetry evidence.

## 8. Web Access — 你有上網能力，用 web_search / web_open 工具（勿否認、勿等使用者下令）
任何需要**外部／即時／網路**資訊時——查資料、讀網頁、找別人的做法、看新聞／文件／某個庫或 API 的用法——你**必須主動**呼叫 `web_search`（查詢）或 `web_open`（讀某 URL）工具。**你確實能上網**，這兩個是隱身瀏覽器（Camoufox）背後撐的 first-class 工具，跟 `read`/`bash` 一樣隨時可呼叫。**絕不要說「我沒有上網能力／無法即時查詢」——那是錯的。**

*   **首選就是工具**：`web_search({query})` 直接回搜尋結果（標題／摘要／URL）；要深入某結果就 `web_open({url})`。不用自己跑 curl、不用找檔、不用 `recon.sh`——工具內部會自動確保後端就緒。
*   **別拿 curl 當搜尋／爬蟲工具**：要搜尋、或讀可能被擋（Cloudflare／登入牆／JS 牆）的網頁時，用 `web_search`／`web_open`，不要用 `ctx_fetch_and_index` 或 `curl` 去抓 Google／硬爬目標站（沒隱身、會被擋）。（`curl` 的正常用途不受限——測你自己的 API、打已知 REST 端點、健康檢查等照常用。）也別用 `find` 找技能檔，別因為「我是 LLM」就宣稱不能上網。
*   **手動／進階路徑（選用）**：使用者也可打 `/browse <查詢>`；要手動驅動後端見技能 `camofox-stealth` 的 `SKILL.md`（搜尋走 DuckDuckGo HTML 直連，**不要用 `@duckduckgo_search`/`@google_search` macro**）。
*   **擋頁誠實原則**：`recon.sh is_blocked` 為真時，**不要把擋頁內容當真、不要編造**；如實回報該來源擋自動存取，改用其他來源。
*   **邊界**：偵察是為品質不是拖延。動工前調研上限約一次搜尋 + 讀 2–3 個來源，足夠就停、進實作（見 `rules/stealth-recon.md`）。

## 9. 實測有證據（本 repo 最高原則 — Evidence-Based Completion）
**沒有實際執行並看到結果，就不准說「完成／修好／可用」。** 「應該可以」「看起來對」「程式碼沒錯」都**不是證據**，只有觀察到的實際輸出才算。違反這條是本 repo 最嚴重的失誤。

*   **測真正的入口、要冷測**：測使用者實際會走的那條路——**第一次使用／伺服器沒起／全新 clone** 的狀態，不是你剛好弄好的「已暖機」狀態。（教訓：`web_search` 之所以「能用」只因後端是先手動起好的；冷啟動的 `spawn sh ENOENT` 從沒被測，對每台新機都是壞的。）
*   **「我這台是綠的」不算證明**：環境會不同——PATH、gitignored 檔案、OS。宣稱通過前先重現目標環境。（教訓：一個測試讀了 gitignored 的 `pi-config/settings.json`，本機過、CI 全新 checkout 全炸。）
*   **把證據亮出來**：回報完成時，貼出**實際跑的指令**與**實際輸出**。沒跑就老實說沒跑，不要暗示你沒做的驗證。
*   **數字與宣稱一律先跑再寫**：報告或 **commit 訊息**裡的任何具體數字（「N tests pass」「涵蓋 X 檔」「快 3 倍」）或成功宣稱，必須來自**下筆當下的實際執行**，不是預估或記憶。要寫數字就先跑、用真值；無法當場驗證就別寫具體數字。（教訓：commit 寫「125 tests」是預估，實跑 127。）
*   **改完程式一定跑 `python -m unittest discover -s tests`**；動到 extension／skill 就實際觸發那條路徑看輸出。CI 紅燈抓到真 bug 是它在做正事，修 bug，別當噪音。

## 10. 能力善用（Capability-First，方法論優先 — 讓已裝的方法論與工具真的被觸發）
本 repo 的增強能力分**三維度**（完整說明見 README「核心功能」）。能力在、沒被觸發＝等於沒有（camofox 教訓）。**流程／方法論先於實作**——先定調「怎麼做」，再動手。動手前依情境主動叫用（下列技能名皆已核實可載入）：

### 維度一 · 安全治理與工程紀律
*   **ECC hooks（主動阻擋，經 `ecc-hooks-bridge`）**：在 `tool_call` 時實際擋下三類——`git push --no-verify`（block-no-verify）、弱化設定（config-protection）、未調查就動危險操作（GateGuard「先調查」）。被擋＝照它給的理由去調查／改法，**別想繞過**。
*   **YES.md ＝ `yes` 技能（行為紀律；本 harness 只掛技能、未掛其 hooks，故非 `.env` 白名單）**：當你改檔案／設定／部署、想沒證據就猜（「應該是／可能」）、想推給使用者、改完沒驗證就報完成、有工具卻不用、或原地打轉時——遵它。與 §8（用工具）／§9（實測有證據）同源。
*   做新東西／創意工作 → `brainstorming` 釐清意圖 → `planning-with-files`／`writing-plans` 立計畫。
*   有 bug／非預期行為 → `systematic-debugging`（先復現、定位根因，別亂修）；實作功能或修 bug → `test-driven-development`（先寫會失敗的測試）。

### 維度二 · 工作流與上下文
*   有邊界的多任務專案／cwd 有 `CASE.md` 或 `00_Constitution` → `case-framework`（憲法-架構-狀態-執行）；`planning-with-files` 巢狀其任務目錄內（見 §4）。
*   複雜多步任務（>5 步或跨多檔）→ `planning-with-files`（task_plan／findings／progress）。
*   有取捨／多角度／多方利害的決策 → 輕量 `thinking-frameworks`；重大或多方上 `mece-autopilot`；要矛盾／辯證對照用 `contradiction-analysis`。
*   對話中冒出可留存的新知 → `hello-reflect` 寫入規範檔；長對話省 token → `caveman`。

### 維度三 · 本地工具
*   問架構／檔案關係／god node → `graphify`（先讀 `graphify-out/GRAPH_REPORT.md`）。
*   累積長文件／日誌要檢索 → `llm-wiki`。
*   反覆失敗的 prompt 模式 → `darwin-skill`／`capability-evolver` 演化。

*   **寫／改技能本身** → `writing-skills` ＋ §6 的 GEPA 分支流程。**宣稱完成前** → §9 實測有證據。

原則：瑣碎任務（單行改、格式修）不強制；非瑣碎、會影響行為的工作，先定方法再動手。不確定用哪個，先用 `thinking-frameworks` 過一遍。
