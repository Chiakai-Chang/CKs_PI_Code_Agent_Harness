# 🧠 跨平台全能裝束 (Universal Harness) 戰略研討會

## 角色模擬討論 (Persona Dialogue)

**Architect (系統架構師)**:
> 「目前的問題在於我們太依賴 `gemini-extension.json` 和 `GEMINI.md`。如果我們要套在 Claude Code 上，它認的是 `.claude/skills/`；Codex 則認 `.codex/`。我們需要一個 **『統一描述層 (Unified Manifest)』**。核心邏輯（大師們的 Markdown）不動，但『交付方式』要抽象化。我們的目標是做到：**『一套核心，多種投影』**。」

**Bridge Engineer (橋接工程師)**:
> 「沒錯！而且工具名稱也不一樣。Gemini 是 `read_file`，Claude 是 `Read`。我建議建立一個 **『工具轉譯層 (Tool Translator)』**。在每個環境載入時，動態生成一份適配該環境的工具映射表。這樣大師們寫的 Prompt 就不用針對每個平台寫死工具名，而是使用我們定義的通用介面。」

**UX Designer (使用者體驗專家)**:
> 「安裝流程必須極致簡化。使用者不應該管它是給誰用的。`install.sh` 應該具備 **『環境嗅探 (Environment Detection)』** 能力。自動偵測當前目錄或全域安裝的是哪種 CLI，然後自動執行對應的映射。理想狀態是：`git clone` 之後按一下 Enter，全平台就位。」

---

## 核心設計理念：環境自適應投影 (Environment Projection)
參考 `DISTILLATION_GUIDE.md` 的理念，我們不進行功能閹割，而是進行 **「邏輯與平台的分離」**。

### 1. 理想狀態 (Ideal State)
*   **平台無關的核心層 (`/core`)**：存放所有從大師那裡蒸餾來的 Markdown 技能與規則。
*   **自適應橋接層 (`/bridges`)**：針對 Claude, Codex, Gemini 分別提供適配器。
*   **一鍵部署 (One-Click)**：安裝腳本自動識別環境並完成 Symlink 映射。

### 2. 需求規格 (Requirements Specification)
*   **REQ-01**: 支援自動偵測 `claude`, `codex`, `pi` 指令是否存在。
*   **REQ-02**: 將 `pi-extensions/` 重新組織為可支援多平台的 `harness-extensions/`。
*   **REQ-03**: 提供工具映射宏（Macros），解決 `read_file` vs `Read` 的差異。
*   **REQ-04**: 維持現有的「智慧映射 (Map-Driven Restore)」優勢，不複製大型外部資產。

---
**本研討會紀錄將作為 v4.0 SAD (軟體架構文件) 的基礎。**
