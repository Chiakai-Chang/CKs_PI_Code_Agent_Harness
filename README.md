# CK's Pi Code Agent Harness

用於 [Pi Coding Agent](https://github.com/badlogic/pi-mono) 的配置增強與外部模組管理工具。

本專案透過 `Git Submodule` 與橋接（Bridge）機制，整合並載入多個外部 Agent 相關開源倉庫的方法論與最佳實踐。這是一套針對本地 AI 開發環境的**通用增強配置**，旨在提升 AI 的工程紀律、工作流控制與記憶體管理效率。

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

> 安裝腳本會自動引導您選擇設定檔，並將相關的 skills 和 extensions 註冊複製到 `~/.pi/agent` 中。

### 3. 設定檔選擇 (Skill Profile)
在部署過程中，您可以選擇以下兩種模式：
*   **`minimal`** (極簡核心)：僅載入 Core 核心 + Caveman 極簡 Token 防禦。通用於所有程式語言，最省對話 Token。
*   **`standard`** (預設標準版)：在極簡核心之上，載入通用軟體工程紀律（TDD/Plan/Debug）與專案知識庫功能，100% 語言無關，適合日常通用開發。

### 4. 開始開發
```bash
pi
```

---

## 🛠️ 核心功能特性

本專案圍繞著 **工程紀律**、**記憶體與工作流管理** 和 **本地化工具** 提供以下核心能力：

### 1. 🛡️ 工程紀律與安全治理
*   **紀律守護 (ECC Hooks)**：掛載 Git 鉤子 (hooks)，在 AI 執行高風險操作（如語法錯誤、金鑰外洩、危險指令）前攔截並報錯。
*   **工程方法論 (Superpowers)**：引導 AI 採用 TDD 測試驅動與系統化規劃，防止 AI 隨意且無效地重構代碼。
*   **安全攔截 (YES.md)**：精準的安全規則庫，防止 AI 讀寫或破壞系統關鍵檔案。

### 2. 🧠 記憶體與工作流優化
*   **環境治理 (C.A.S.E. Framework)**：基於「憲法-架構-狀態-執行」的檔案驅動任務管束協定，限制 AI 的行為與環境邊界。
*   **任務套疊 (CASE & PWF)**：結合 Planning-with-Files 規劃，將注意力檔案嵌套於任務包中，避免並行任務時的注意力干擾。
*   **海馬迴自我演進 (hello-reflect)**：自動偵測對話中的學習點，將其固化並更新至 `CLAUDE.md` 以實現知識複利。
*   **上下文剪裁 (Context Kernel & Caveman)**：內建上下文裁切指引，並使用 Caveman 極簡語音壓縮技術，降低長對話中的 Token 消耗量。

### 3. 🔍 本地化工具與效能
*   **AST 圖譜導航 (Graphify)**：使用本地輕量 Tree-sitter 分析原始碼並產生 AST 拓撲，降低大範圍檢索時的 API Token 消耗。
*   **專案 Wiki (LLM Wiki)**：將長篇參考文件或日誌整理為雙向鏈接的原子化 Wiki，供 AI 按需檢索。
*   **提示變異優化 (Darwin & Evolver)**：實驗性的 Prompt 演化演算法，藉由掃描失敗模式進行 Prompt 變異自演化。

---

## 📂 整合之外部倉庫與來源

本專案藉由 Git Submodule 與橋接（Bridge）機制，將以下開源倉庫的最佳實踐有機融合：

| 領域 | 來源倉庫 | 導入方式 | 核心評估功能 |
| :--- | :--- | :--- | :--- |
| **工程紀律** | [ECC](https://github.com/affaan-m/ECC) | Git Submodule | 文件安全審查與自動品質門檻限制。 |
| **工作流** | [Planning-with-Files](https://github.com/OthmanAdi/planning-with-files) | Git Submodule | 實體任務規劃檔案與會話狀態快照。 |
| **專案知識** | [LLM Wiki](https://github.com/praneybehl/llm-wiki-plugin) | Git Submodule | 原子化知識庫沉澱與雙向鏈接文件。 |
| **方法論** | [Superpowers](https://github.com/obra/superpowers) | Git Submodule | 通用 TDD 方法論、單元測試、Git 微步提交引導。 |
| **資源防禦** | [Caveman](https://github.com/JuliusBrussee/caveman) | Git Submodule | 極簡語音壓縮，降低 Context 消耗量。 |
| **行為準則** | [Karpathy](https://github.com/forrestchang/andrej-karpathy-skills) | Git Submodule | 避開常見寫入衝突的通用開發指引。 |
| **提示工程** | [Prompt Master](https://github.com/nidhinjs/prompt-master) | Git Submodule | 通用提示詞優化範本。 |
| **安全治理** | [YES.md](https://github.com/sstklen/yes.md) | Git Submodule | 命令安全性攔截與防呆 Hooks。 |
| **美學/UX** | [Taste Engine](https://github.com/Leonxlnx/taste-skill) | Git Submodule | 載入設計樣式與視覺引導。 |
| **基因優化** | [Evolver](https://github.com/EvoMap/evolver) | Git Submodule | 失敗模式掃描與抗體 prompt 演化。 |
| **提示微調** | [Darwin](https://github.com/alchaincyf/darwin-skill) | Bridge (橋接) | 實驗性 Prompt 演化演算法。 |
| **辯證分析** | [Qiushi](https://github.com/HughYau/qiushi-skill) | Bridge (橋接) | 控制組行為比對分析。 |
| **除錯實踐** | [Best Practices](https://github.com/DenisSergeevitch/agents-best-practices) | Bridge (橋接) | 系統化除錯與規則簡化引導。 |
| **圖譜導航** | [Graphify](https://github.com/safishamsi/graphify) | Bridge (橋接) | 本機 AST 結構分析圖譜導航。 |
| **循環工程** | [Loopy](https://github.com/Forward-Future/loopy) | Bridge (橋接) | 工作流閉環控制 playbooks。 |
| **環境治理** | [C.A.S.E.](https://github.com/Chiakai-Chang/Local-Agent-Workspace/tree/main/C.A.S.E._Framework) | Bridge (橋接) | 憲法-架構-狀態-執行（C.A.S.E.）檔案驅動任務管束協定。 |

---

## 🛡️ 隱私與安全限制

*   **本地優先**：所有配置與 Tree-sitter 分析完全在本地運行，不向第三方洩漏代碼結構。
*   **防寫保護**：預防 AI 任意修改或刪除系統關鍵環境變數（如 `.env`）與敏感設定。
*   **完全透明**：所有掛載的 hooks 與行為約束規則皆完全開源且透明可檢視。

---

## 🙏 感謝與授權

*   **專案授權**：本專案採用 **MIT 授權**。
*   **開源感謝**：感謝所有被整合倉庫的作者與開源貢獻者。每一項整合模組皆配有 `RATIONALE.md` 以紀錄評估決策。

---
**由 [CK (Chiakai Chang)](https://github.com/Chiakai-Chang) 維護。本專案純屬實驗性質，旨在探索 AI 開發流程的具體配置可能性。**
