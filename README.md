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
> 啟動時若見到 `[Skill conflicts]` 名稱警告，多為上游命名問題、技能仍正常載入，詳見 [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)。

### 解除安裝 (Uninstall)
*   **只移除 harness 管理項**（保留你自己的技能與 `~/.camofox` 登入資料）：`python scripts/uninstall.py`
*   **完整刪除、重來**（逐項確認，可額外刪 `~/.camofox`、備份、Pi 本體）：`python scripts/uninstall.py --purge`
    — 最後會提示手動刪除 repo 資料夾。

### 4. 模式選擇 (Profiles)
安裝時可依需求選擇以下配置模式：
*   **`minimal`** (極簡核心)：適合對對話 Token 敏感的輕量開發。
    *   📦 **僅載入**：`Core 核心`（含 `hello-reflect` 自我演進）、`Caveman`（極簡對話防護）、`ECC`（通用工程實踐）。
*   **`standard`** (預設標準版)：適合日常通用軟體開發。
    *   📦 **載入項目**：包含本專案整合之**所有 17 個外部子模組**與所有本地擴充（TDD 方法論、Wiki 知識庫、AST 圖譜導航等）。
---

## 🛠️ 核心功能

本專案將 AI 增強功能分為三大維度，兼顧開發效率與系統安全性：

### 1. 🛡️ 安全治理與工程紀律
*   **紀律守護 (ECC)**：在 AI 執行高風險操作（語法錯誤、金鑰外洩、敏感指令）前自動攔截。
*   **工程方法論 (Superpowers)**：強迫 AI 遵循 TDD 測試驅動與規劃步驟，避免無效代碼重構。
*   **指令攔截 (YES.md)**：設定白名單與防呆 Hooks，禁止 AI 修改系統關鍵配置或變數檔（.env）。

### 2. 🧠 工作流與上下文優化
*   **任務管束 (C.A.S.E.)**：利用「憲法-架構-狀態-執行」檔案協定，為 AI 劃定清晰的任務邊界。
*   **任務套疊 (CASE & PWF)**：解決並行開發時注意力污染的問題，將任務上下文獨立隔離。
*   **海馬迴進化 (hello-reflect)**：自動從對話中提煉新知識並寫入規範檔案（如 `CLAUDE.md`、`.agents/AGENTS.md`、`.cursorrules` 等），實現規則自演進。
*   **Token 節約 (Caveman)**：對上下文進行無損語意壓縮，大幅延長長對話的 Token 生命期。

### 3. 🔍 本地化工具
*   **AST 圖譜導航 (Graphify)**：利用 Tree-sitter 分析代碼 AST 拓撲，降低檢索代碼時的 API 消耗。
*   **專案 Wiki (LLM Wiki)**：建立雙向鏈接的原子化 Wiki，協助 AI 快速檢索長篇日誌與文件。
*   **提示變異 (Darwin & Evolver)**：針對失敗的對話模式進行 Prompt 自我演變與抗體生成。

---

## 📂 整合外部倉庫

本專案整合了以下開源專案與方法論的最佳實踐（圖示：✅ 完全啟用 \| ⚠️ 僅核心子集 \| ❌ 未載入）：

| 領域 | 來源專案 / 概念 | 導入方式 | 核心功能 | Minimal | Standard |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **工程紀律** | [ECC](https://github.com/affaan-m/ECC) | Git Submodule | 安全審查與品質門檻 | ⚠️ | ✅ |
| **工作流** | [Planning-with-Files](https://github.com/OthmanAdi/planning-with-files) | Git Submodule | 任務規劃與狀態快照 | ❌ | ✅ |
| **專案知識** | [LLM Wiki](https://github.com/praneybehl/llm-wiki-plugin) | Git Submodule | 知識庫沉澱與鏈接文件 | ❌ | ✅ |
| **方法論** | [Superpowers](https://github.com/obra/superpowers) | Git Submodule | TDD 方法論與微步提交 | ❌ | ✅ |
| **資源防禦** | [Caveman](https://github.com/JuliusBrussee/caveman) | Git Submodule | Token 壓縮防禦 | ⚠️ | ✅ |
| **行為準則** | [Karpathy](https://github.com/multica-ai/andrej-karpathy-skills) | Git Submodule | LLM 寫入防護指引 | ❌ | ✅ |
| **提示工程** | [Prompt Master](https://github.com/nidhinjs/prompt-master) | Git Submodule | 提示詞優化範本 | ❌ | ✅ |
| **安全治理** | [YES.md](https://github.com/sstklen/yes.md) | Git Submodule | 指令安全與攔截 Hooks | ❌ | ✅ |
| **美學/UX** | [Taste Engine](https://github.com/Leonxlnx/taste-skill) | Git Submodule | 設計樣式與視覺引導 | ❌ | ✅ |
| **基因優化** | [Evolver](https://github.com/EvoMap/evolver) | Git Submodule | 失敗模式與 Prompt 演化 | ❌ | ✅ |
| **提示微調** | [Darwin](https://github.com/alchaincyf/darwin-skill) | Bridge (橋接) | Prompt 變異優化 | ❌ | ✅ |
| **辯證分析** | [Qiushi](https://github.com/HughYau/qiushi-skill) | Bridge (橋接) | 重構前後對照分析 | ❌ | ✅ |
| **除錯實踐** | [Best Practices](https://github.com/DenisSergeevitch/agents-best-practices) | Bridge (橋接) | 系統化除錯引導 | ❌ | ✅ |
| **圖譜導航** | [Graphify](https://github.com/safishamsi/graphify) | Bridge (橋接) | AST 本地圖譜分析 | ❌ | ✅ |
| **循環工程** | [Loopy](https://github.com/Forward-Future/loopy) | Bridge (橋接) | 工作流閉環控制 | ❌ | ✅ |
| **環境治理** | [C.A.S.E.](https://github.com/Chiakai-Chang/Local-Agent-Workspace/tree/main/C.A.S.E._Framework) | Bridge (橋接) | C.A.S.E. 任務管束協定 | ❌ | ✅ |
| **多維推理** | [MECE-Autopilot](https://github.com/Chiakai-Chang/MECE-Autopilot) | Bridge (橋接) | 互斥窮盡多角色辯論與收斂 | ❌ | ✅ |
| **記憶進化** | [claude-reflect](https://github.com/BayramAnnakov/claude-reflect) | 本地移植 (蒸餾) | 專案規則檔案自演進 | ✅ | ✅ |
| **隱身瀏覽** | [camofox-browser](https://github.com/jo-inc/camofox-browser) | Thin Bridge (橋接) | 隱身瀏覽器（Camoufox 反偵測）：搜尋、讀頁、點擊/輸入/捲動、截圖、頁內 JS、多分頁、建立登入態；可穿 Cloudflare/JS 牆。工具 `web_*`、命令 `/weblogin`、技能 `camofox-stealth`（首次用時懶下載 ~300MB 引擎） | ❌ | ✅ |

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
