# CK's Pi Code Agent Harness

用於 [Pi Coding Agent](https://github.com/badlogic/pi-mono) 的配置增強與外部模組管理工具。

本專案透過 `Git Submodule` 與 `Bridge Extension`（橋接擴充套件）方式，整合並載入多個外部 Agent 相關開源倉庫的方法論。這是一套實驗性的整合配置，旨在探索如何結合不同的控制迴圈、記憶體架構與工作流規範以協助 AI 執行任務。

---

## 🏗️ 主要功能模組與特徵

本專案嘗試在開發環境中整合以下功能特徵：

1.  **🛡️ 紀律守護 (ECC Hooks)**：掛載預提交鉤子，在 AI 執行高風險操作（如語法錯誤、金鑰洩漏）前攔截並報錯。
2.  **🧠 工程方法論 (Superpowers)**：引導 AI 採用 BDD/TDD 測試驅動與系統化規劃步驟。
3.  **🔍 AST 代碼結構圖譜 (Graphify)**：使用本機輕量 Tree-sitter 分析原始碼，產生 AST 拓撲關係，降低搜尋時的 API Token 消耗。
4.  **📚 專案 Wiki (LLM Wiki)**：將大篇幅參考文檔或日誌整理為原子化的 Wiki 網頁，供 AI 按需檢索。
5.  **📝 狀態與沙盒管理 (C.A.S.E. & PWF)**：嵌套 Planning-with-Files 規劃檔案於 C.A.S.E. 的 `02_Task_Queue` 沙盒任務包內，限制讀寫範圍，防止多任務並行時的記憶污染。
6.  **🏭 多代理編排 (OMC Teams)**：設定多角色代理人模板，便於在需要時調用 Checker、Architect 等角色。
7.  **🧪 矛盾對照分析 (Qiushi)**：引入矛盾論分析原則，要求對代碼重構前後的行為建立嚴格對照組，進行行為核對。
8.  **🧬 自演進實驗 (SkillClaw & Darwin)**：實驗性結合 SkillClaw（跨 session 軌跡清理與 SKILL.md 結構去重）與 Darwin（沙盒分支 Prompts 變異調優）。
9.  **🧭 需求核對 (PM Skills)**：載入多種產品分析與需求驗收框架，用於在規劃階段對齊 Acceptance Criteria。

---

## 📂 已整合的外部模組與倉庫

本專案透過 Git Submodule 連結以下倉庫：

| 領域 | 來源專案 | 導入方式 | 評估目的 / 預期功能 |
| :--- | :--- | :--- | :--- |
| **工程紀律** | [ECC](https://github.com/affaan-m/ECC) | Submodule (Path 1) | 特種代理人模板、文件安全審查與自動品質門檻。 |
| **方法論** | [Superpowers](https://github.com/obra/superpowers) | Submodule (Path 1) | TDD 方法論、單元測試、Git 微步提交引導。 |
| **行為準則** | [Karpathy](https://github.com/forrestchang/andrej-karpathy-skills) | Submodule (Path 1) | 避開常見 LLM 卡死與寫入衝突的開發指南。 |
| **認知提取** | [Nuwa (女媧)](https://github.com/alchaincyf/nuwa-skill) | Submodule (Path 1) | 專家視角思維模型。 |
| **TS 專家** | [Matt Pocock](https://github.com/mattpocock/skills) | Submodule (Path 1) | TypeScript 類型重構與診斷。 |
| **Web 效能** | [Addy Osmani](https://github.com/addyosmani/agent-skills) | Submodule (Path 1) | 瀏覽器效能指標審計與 API 契約設計規則。 |
| **提示工程** | [Prompt Master](https://github.com/nidhinjs/prompt-master) | Submodule (Path 1) | 指令優化與跨模型指令翻譯模板。 |
| **CLI 標準** | [Printing Press](https://github.com/mvanhorn/cli-printing-press) | Submodule (Path 1) | 精簡代理人輸出，減少金鑰使用量。 |
| **BDD 實踐** | [AIxBDD](https://github.com/Waterball-Software-Academy/aixbdd) | Submodule (Path 1) | 行為驅動測試與規格自動對齊。 |
| **能動性規範** | [PIP Guardian](https://github.com/tanweai/pua) | Submodule (Path 1) | 限制 AI 偷懶或敷衍指令。 |
| **代理編排** | [OMC](https://github.com/Yeachan-Heo/oh-my-claudecode) | Submodule (Path 1) | 團隊協作與會話持久化管理。 |
| **安全治理** | [YES.md](https://github.com/sstklen/yes.md) | Submodule (Path 1) | 命令安全性攔截與防呆 Hooks。 |
| **美學/UX** | [Taste Engine](https://github.com/Leonxlnx/taste-skill) | Submodule (Path 1) | 載入設計樣式與視覺引導。 |
| **產品分析** | [PM Skills](https://github.com/phuryn/pm-skills) | Submodule (Path 1) | 專案路線圖分析與驗收準則制定。 |
| **基因優化** | [Evolver](https://github.com/EvoMap/evolver) | Submodule (Path 1) | 失敗模式掃描與抗體 prompt 演化。 |
| **提示微調** | [Darwin](https://github.com/alchaincyf/darwin-skill) | Bridge (Path 2) | 實驗性 Prompt 演化算法。 |
| **辯證分析** | [Qiushi](https://github.com/HughYau/qiushi-skill) | Bridge (Path 2) | 控制組行爲比對分析。 |
| **除錯實踐** | [Best Practices](https://github.com/DenisSergeevitch/agents-best-practices) | Bridge (Path 2) | 系統化除錯與規則簡化引導。 |
| **智慧演進** | [SkillClaw](https://github.com/AMAP-ML/SkillClaw) | Bridge (Path 2) | 跨會話軌跡去重與 SKILL.md 自動重構。 |
| **圖譜導航** | [Graphify](https://github.com/safishamsi/graphify) | Bridge (Path 2) | 本機 AST 結構分析圖譜導航。 |
| **循環工程** | [Loopy](https://github.com/Forward-Future/loopy) | Bridge (Path 2) | 工作流閉環控制 playbooks。 |
| **環境治理** | [C.A.S.E.](https://github.com/Chiakai-Chang/Local-Agent-Workspace) | Bridge (Path 2) | 唯讀/讀寫沙盒結構與雙軌驗證協定。 |

---

## 🚀 快速上手 (Quick Start)

### 1. 取得專案
```bash
git clone --recursive https://github.com/Chiakai-Chang/CKs_PI_Code_Agent_Harness.git
cd CKs_PI_Code_Agent_Harness
```

### 2. 部署配置
*   **Windows**: 執行 `install.bat`。
*   **macOS / Linux**: 執行 `bash install.sh`。

> 安裝腳本會讀取 `pi-config/settings.json`，將 submodule 中的 skills/extensions 註冊並複製到 `~/.pi/agent` 中。

### 3. 開始開發
```bash
pi
```

---

## 🛠️ 核心功能特點

*   **⚡ Map-Driven Restore**：動態尋址映射，避免寫死本機路徑。
*   **🧠 Context Kernel**：內建上下文剪裁與壓縮指引，以節省長對話中的 Token 費用。
*   **🧠 C.A.S.E. 嵌套沙盒**：限制 AI 在指定任務目錄下讀寫，避免對整個 workspace 造成覆蓋。
*   **🧠 AST 圖譜分析 (Graphify)**：使用本機 Tree-sitter 提供程式碼結構導航。
*   **🧠 Hippocampus (海馬迴)**：整合 `hello-reflect`，自修復 `CLAUDE.md`。
*   **🕵️ Stealth Force**：整合 `camofox-stealth` 的瀏覽適配。
*   **📑 Rationale Archive**：每一項整合模組皆配有 `RATIONALE.md`，說明當初遷移與評估的決策。

---

## ✅ 隱私與安全

*   **本地優先**：支援本地推理引擎（Ollama/llama.cpp）的配置適配。
*   **安全防禦**：設定防寫目錄與預防刪除重要環境變數檔案（.env）的安全規則。
*   **完全開源**：所有規則與腳本皆透明可見。

---

## 🙏 感謝與授權

*   本專案採用 **MIT 授權**。
*   感謝所有被整合倉庫的作者與開源貢獻者。

---
**由 [CK (Chiakai Chang)](https://github.com/Chiakai-Chang) 維護。本專案純屬實驗性質，旨在探索 AI 開發流程的具體配置可能性。**
