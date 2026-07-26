# 🏛️ Harness OS 與 Pi 原生架構整合與共存指南 (Harness OS Integration & Coexistence Guide)

這份文件以 **MECE (相互獨立、完全窮盡)** 邏輯框架，詳細說明 **CK's Pi Code Agent Harness** 與原生 **Pi Coding Agent 引擎** 之本質關係、運行生命週期作用機制，以及當使用者自訂其他 Skills、Extensions 或第三方 Harness 時的隔離共存保護策略。

---

## 1. 本專案與 Pi 平台的本質關係 (Relationship)

本專案與原生 Pi 引擎 **非競爭關係**，亦 **非單純的第三方技能列表**，而是 **「Pi 引擎的操作系統與約束框架 (Harness OS for Pi Engine)」**。

```
+-----------------------------------------------------------------------------------+
|                        CK's Pi Code Agent Harness (本專案)                        |
|                                                                                   |
|  [Layer 0 Protection]    [Layer 1 Socratic]    [Layer 2 Context Engine]            |
|  • yes-hooks-bridge      • grilling-protocol   • minimal-prompt-guide (~100t)      |
|  • pre-bash-guard        • contrarian-review   • compact-continuation-bridge        |
|  • skill-namespace-guard • adversary-review    • hello-reflect (自演進)            |
|                                                                                   |
|  [Layer 3 Execution/Repair/Research]           [Layer 4 Evidence Gate]            |
|  • browser-automation & deep-research-guide    • autonomous-experiment (MAD)      |
|  • tool-repair-guide (9 Canonical Repairs)     • harness-factory-guide (Darwin)    |
|  • ide-intelligence-guide (LSP/Edit)           • 173 Unit Tests 防護網            |
+-----------------------------------------------------------------------------------+
                                         │
                   注入與管控 (.pi/agent/ & settings.json)
                                         ▼
+-----------------------------------------------------------------------------------+
|                     Pi Agent Runtime Host (原生 Pi 引擎)                          |
|  • Tools Engine (Tool Call, LSP, Shell, File System)                              |
|  • Context Window & Compactor (/compact)                                          |
|  • Extension Hook System (before_agent_start, tool_call, event_bus)               |
+-----------------------------------------------------------------------------------+
```

### 職責對比矩陣

| 維度 | Pi (原生平台引擎) | 本 Harness (CK's Harness OS) |
| :--- | :--- | :--- |
| **角色定位** | 執行引擎與工具底座 (Engine / CPU) | 駕駛艙與守護框架 (Harness OS) |
| **職責範圍** | 提供基礎工具、模型 API 介面、 Context 管理與指令解析 | 注入工程紀律、行為守護、記憶自演進與工具欄位自癒 |
| **運作層次** | 底層能力 (I/O, Shell, LLM 傳送) | 高階邏輯 (Layer 0–4 閉環控制、門控與對立審查) |
| **獨立性** | 裸機啟動，依賴 LLM 自律 | 腳本硬封鎖高風險指令、強制一問一答與證據驗證 |

---

## 2. Pi 安裝後，本專案如何發揮作用 (Runtime Lifecycle)

本專案透過 `scripts/setup.py` 與 `scripts/restore.py` 的自動化部署，在 Pi 啟動與運行的四個階段實體干預並引導：

```
[Phase 1: Session Init] ──► [Phase 2: Prompting] ──► [Phase 3: Execution] ──► [Phase 4: Post-Session]
  • namespace-guard           • minimal-prompt       • pre-bash-guard         • hello-reflect
    比對碰撞與隔離               (注意力專注)           (硬擋高風險指令)           (規則自提煉)
  • validate-config           • Socratic framing     • tool-repair            • HANDOFF.md
    快照與模型檢查               (需求研討門控)         (9大欄位修復)             (斷點保存)
```

### 階段一：啟動檢查與隔離 (Session Initialization)
* **`skill-namespace-guard`**：於每次 `pi` 啟動時前置觸發，自動比對用戶全域技能與本 Harness 外部技能，將同名碰撞項目進行平滑隔離。
* **`validate-config.py`**：靜態檢查配置 Integrity、模型狀態與路徑正確性。

### 階段二：提示與需求門控 (Prompting & Framing)
* **`minimal-prompt-guide`**：控制 System Prompt 預算在 **~80-200 Token**，將模型注意力極限聚焦於當前任務。
* **`grilling-protocol`**：強制進行一問一答需求釐清，在取得不可變 Evidence QA 門控前嚴禁直接改動代碼。

### 階段三：執行、研究與自癒 (Execution, Research & Tool Repair)
* **`yes-hooks-bridge` / `pre-bash-guard`**：在 Shell 執行前**硬性攔截高風險指令**（`rm -rf /`、`git push --force`）。
* **`deep-research-guide` / `browser-automation-guide`**：控制網頁深度搜資與 AX-Tree 語意定位。
* **`tool-repair-guide`**：攔截無效 JSON 與缺少必要欄位的 Tool Call，自動嘗試 9 大 Canonical 欄位備援修復。

### 階段四：壓縮續作與海馬迴進化 (Compaction & Memory Evolution)
* **`compact-continuation-bridge`**：當 Session 發生 `/compact` 上下文壓縮時，自動注入續接指令，避免 Agent 中途停工。
* **`hello-reflect`**：從每一次對話結論中提煉規範與知識，自動寫入 `.agents/AGENTS.md` / `CLAUDE.md`。

---

## 3. 與用戶自訂/第三方資源的隔離共存矩陣 (MECE Coexistence Matrix)

我們針對用戶引入外部資源的三種維度（Skills, Extensions, External Harnesses）進行 MECE 評估與防護機制設計：

### 維度 A：用戶自行安裝其他 `Skills`
* **潛在衝突**：用戶全域 `~/.pi/agent/skills/` 裝了同名 Skill（如用戶也裝了自己的 `caveman` 或 `browser-automation`）。
* **本專案防禦與處理機制**：
  1. **動態抽離 (`partition_external_skills`)**：`restore.py` 執行時，自動將 `external/*` 的技能抽離寫入 `pi-config/external-skills-manifest.json`，不硬塞入 `settings.json` 的固定清單。
  2. **動態檢索門控 (`skill-namespace-guard`)**：啟動時現場比對用戶技能與專案技能。若發現碰撞，**永遠優先保護用戶的自訂 Skill**，將專案衝突技能改名或降級載入，絕不強行覆蓋用戶檔案。

### 維度 B：用戶自行安裝其他 `Extensions` (TypeScript Hooks)
* **潛在衝突 1：Tool Name 碰撞**（例如用戶裝了另一個提供 `web_search` 的 Extension）。
  - **處置**：[scripts/restore.py](../../scripts/restore.py) 中，`profile_extensions`（包含 `stealth-web-bridge`）**絕對不重複寫入 `settings.json` 的 `extensions` 陣列**。所有 Harness 內建 Bridges 統一物理複製至 `~/.pi/agent/extensions/<bridge>/` 由 Pi 自動單一來源載入，徹底消除雙重加載導致的 `registerTool()` 重複註冊崩潰（解決了「Tool web_search conflicts with...」問題）。
* **潛在衝突 2：Hook Event 執行鏈**（如 `before_agent_start` 事件順序）。
  - **處置**：採用獨立輕量管道（`yes-hooks-bridge` 獨立註冊預檢），不攔截其他 Extension 的事件傳遞，並以可預期 Exit Code (0 或 1) 做斷路器。

### 維度 C：用戶採用了其他第三方 Harness 框架（如全域裝了 `obra/superpowers` 或 `oh-my-pi`）
* **潛在衝突**：其他 Harness 在全局 `settings.json` 或擴充路徑中注入了強制的行為規則。
* **處置**：
  1. **原生相容免重複 (`superpowers` 免二重註冊)**：針對 `superpowers`，本專案辨識到用戶可能已全局安裝，故在 `restore.py` 中明確將 `external/superpowers` 設為 **純研究參考**，不在 `restore.py` 中重複拷貝，消除 13 個啟動 Skill 衝突警告。
  2. **環境與路徑完全解耦**：所有內建擴充與腳本動態綁定 `PI_HARNESS_ROOT` 環境變數與全域 `AGENT_DIR`，完全維持雙向獨立。

---

## 4. 總結：無痛整合與生態相容承諾

本 Harness 系統具備高度的 **生態包容性 (Coexistence & Self-healing)**：
1. **不搶占、不強蓋**：用戶個人資產優先，衝突自動備份與動態隔離。
2. **硬封鎖、軟調用**：關鍵指令用腳本硬封鎖，一般邏輯用精簡 Prompt 軟指引。
3. **無損續作與演進**：連貫任務自動接關，規則自動寫回本地 Knowledge Base。
