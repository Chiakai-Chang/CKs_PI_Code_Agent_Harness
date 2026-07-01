# CK's Pi Code Agent Harness

用於 [Pi Coding Agent](https://github.com/badlogic/pi-mono) 的配置增強與外部模組管理工具。

本專案透過 `Git Submodule` 與 `Bridge Extension`（橋接擴充套件）方式，整合並載入多個外部 Agent 相關開源倉庫的方法論。這是一套實驗性的整合配置，旨在探索如何結合不同的控制迴圈、記憶體架構與工作流規範以協助 AI 執行任務。

---

## 🏗️ 主要功能模組與特性

本專案嘗試在開發環境中整合以下功能與特性：

1.  **🛡️ 紀律守護 (ECC Hooks)**：掛載 Git 鉤子 (hooks)，在 AI 執行高風險操作（如語法錯誤、金鑰外洩）前攔截並報錯。
2.  **🧠 工程方法論 (Superpowers)**：引導 AI 採用 BDD/TDD 測試驅動與系統化規劃步驟。
3.  **🔍 AST 程式碼結構圖譜 (Graphify)**：使用本機輕量 Tree-sitter 分析原始碼，產生 AST 拓撲關係，降低檢索程式碼時的 API Token 消耗。
4.  **📚 專案 Wiki (LLM Wiki)**：將長篇參考文件或日誌整理為原子化的 Wiki 網頁，供 AI 按需檢索。
5.  **📝 任務執行與狀態管理 (C.A.S.E. & PWF)**：結合 C.A.S.E. 任務管束與 Planning-with-Files 規劃，將注意力記憶檔案套疊於任務包中以防並行任務污染。
6.  **🧪 矛盾對照分析 (Qiushi)**：引入矛盾論分析原則，要求對程式碼重構前後的行為建立嚴格對照組，進行行為核對。
7.  **🧬 自演進與優化實驗 (Darwin & Evolver)**：實驗性結合 Evolver（抗體 Prompt 自演化）與 Darwin（沙盒分支 Prompts 變異最佳化）。

---

## 📂 已整合的外部模組與倉庫

本專案透過 Git Submodule 連結以下倉庫：

| 領域 | 來源專案 | 導入方式 | 評估目的 / 預期功能 |
| :--- | :--- | :--- | :--- |
| **工程紀律** | [ECC](https://github.com/affaan-m/ECC) | Submodule (Path 1) | 文件安全審查與自動品質門檻限制。 |
| **方法論** | [Superpowers](https://github.com/obra/superpowers) | Submodule (Path 1) | 通用 TDD 方法論、單元測試、Git 微步提交引導。 |
| **行為準則** | [Karpathy](https://github.com/forrestchang/andrej-karpathy-skills) | Submodule (Path 1) | 避開常見寫入衝突的通用開發指引。 |
| **提示工程** | [Prompt Master](https://github.com/nidhinjs/prompt-master) | Submodule (Path 1) | 通用提示詞優化範本。 |
| **安全治理** | [YES.md](https://github.com/sstklen/yes.md) | Submodule (Path 1) | 命令安全性攔截與防呆 Hooks。 |
| **美學/UX** | [Taste Engine](https://github.com/Leonxlnx/taste-skill) | Submodule (Path 1) | 載入設計樣式與視覺引導。 |
| **基因優化** | [Evolver](https://github.com/EvoMap/evolver) | Submodule (Path 1) | 失敗模式掃描與抗體 prompt 演化。 |
| **提示微調** | [Darwin](https://github.com/alchaincyf/darwin-skill) | Bridge (Path 2) | 實驗性 Prompt 演化演算法。 |
| **辯證分析** | [Qiushi](https://github.com/HughYau/qiushi-skill) | Bridge (Path 2) | 控制組行為比對分析。 |
| **除錯實踐** | [Best Practices](https://github.com/DenisSergeevitch/agents-best-practices) | Bridge (Path 2) | 系統化除錯與規則簡化引導。 |
| **圖譜導航** | [Graphify](https://github.com/safishamsi/graphify) | Bridge (Path 2) | 本機 AST 結構分析圖譜導航。 |
| **循環工程** | [Loopy](https://github.com/Forward-Future/loopy) | Bridge (Path 2) | 工作流閉環控制 playbooks。 |
| **環境治理** | [C.A.S.E.](https://github.com/Chiakai-Chang/Local-Agent-Workspace/tree/main/C.A.S.E._Framework) | Bridge (Path 2) | 憲法-架構-狀態-執行（C.A.S.E.）檔案驅動任務管束協定。 |

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

### 3. 設定檔選擇 (Skill Profile)

本專案支援兩種設定檔，可於部署時在終端機中進行選擇：
*   **`minimal`** (極簡核心)：僅載入 Core 核心 + Caveman 極簡 Token 防禦。通用於所有程式語言，最省 Token。
*   **`standard`** (預設標準版)：包含上述通用軟體工程紀律與防禦規則，完全語言無關。

### 4. 開始開發
```bash
pi
```

---

## 🛠️ 核心功能特點

*   **⚡ Map-Driven Restore**：路徑動態解析，避免寫死本機路徑。
*   **🧠 Context Kernel**：內建上下文剪裁與壓縮指引，以節省長對話中的 Token 費用。
*   **🧠 C.A.S.E. 任務套疊**：將 PWF 的任務記憶檔案嵌套在 C.A.S.E. 任務包中，避免多任務並行時注意力干擾。
*   **🧠 AST 圖譜分析 (Graphify)**：使用本機 Tree-sitter 提供程式碼結構導航。
*   **🧠 Hippocampus (海馬迴)**：整合 `hello-reflect`，自動修正 `CLAUDE.md`。
*   **🕵️ Stealth Force**：整合 `camofox-stealth` 的瀏覽器適應設定。
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
