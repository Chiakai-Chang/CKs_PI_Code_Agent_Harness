# 🧪 功能蒸餾指南 (Distillation Guide)

這份文件記錄了本專案如何將外部強大的 AI 代理專案（如 `Everything Claude Code`, `Understand-Anything`）「蒸餾」並「移植」到 `Pi` 平台的技術脈絡與心得。

---

## 核心挑戰
大多數先進的 AI 代理專案都是為特定的運行環境（如 Claude Code 原生環境）設計的。直接「複製檔案」通常會導致以下問題：
1.  **路徑失效**：腳本找不到子目錄。
2.  **大腦缺失**：有指令流程 (Skills)，但沒有執行指令的 AI 人格 (Agents)。
3.  **環境摩擦**：Windows 權限、編碼、Git 安全機制等導致流程中斷。

---

## 蒸餾三部曲 (The 3-Step Distillation Process)

### 第一步：架構解構 (Structural Discovery)
不要只看代碼，要看它的「權力結構」。
*   **Skills (靈魂)**：觀察它如何定義操作流程（如 `/understand` 的 Phase 0 到 Phase 7）。
*   **Agents (大腦)**：找出是哪些「人格」在執行這些流程。在 `Understand-Anything` 中，這些是隱藏在 TypeScript 裡的 Prompt 範本；我們必須將其**實體化**為 Pi 可識別的 `.md` 檔案。
*   **Tools (手腳)**：確認它調用了哪些底層指令（Bash, Read, Write）。

### 第二步：橋接與注入 (Bridge & Inject Pattern)
這是本專案的核心發明，確保功能「全域可用」。
*   **橋接 (Bridge Extension)**：建立一個 Pi 專用的 TypeScript 擴充功能，作為「翻譯層」，將 Pi 的事件（如 `tool_call`）對接到外部腳本。
*   **路徑注入 (Absolute Path Injection)**：
    *   **原理**：在安裝階段（`restore.py`），自動獲取本倉庫的「絕對路徑」。
    *   **做法**：將此路徑寫入全域 `settings.json` 的環境變數，或動態修改擴充功能的 `package.json`。
    *   **好處**：AI 不管在哪個硬碟分區執行，都能精準「回家」找到外部功能模組。

### 第三步：環境自癒 (Self-Healing Implementation)
確保「一鍵安裝」是真的可以一鍵完成。
*   **權限自動化**：偵測非管理員權限，主動發起「自我提權重啟」。
*   **編碼強制化**：強制終端機進入 UTF-8 (65001)，消滅中文亂碼。
*   **配置範本化**：提供 `.example` 設定檔，透過腳本自動生成 machine-specific 的真實設定，並透過 `.gitignore` 避免私密設定洩漏。

---

## 未來優化方向：AI 輔助蒸餾
未來若要加入新的功能（例如：[OpenAware](https://github.com/qodo-gen/open-aware)），可以遵循以下自動化檢查：
1.  **[ ] 依賴掃描**：該功能是否依賴特定的外部二進位檔 (Binary)？
2.  **[ ] 人格提取**：是否已在 `agents/` 目錄建立對應的 Markdown 定義？
3.  **[ ] 全域路徑校正**：所有的 `require` 或 `import` 是否能應對跨目錄調用？
4.  **[ ] 互動鎖死檢測**：在巢狀呼叫腳本時，是否會發生「兩個腳本都在等用戶輸入」的死結？

---

## 實戰心得總結
蒸餾的本質不是「搬運」，而是**「重新適配」**。
*   **不要害怕重寫 Agent Prompt**：原始專案的 Prompt 可能太長或不適合 Pi。我們在蒸餾時應提取其「邏輯骨幹」，重構為 Pi 的微型代理 (Micro-Agents)。
*   **保持腳本零依賴**：在 `setup.py` 與 `restore.py` 中，盡量使用 Python 內建庫與系統原生指令（如 `wmic`, `curl`），這能極大降低使用者的門檻。
*   **配置與代碼分離**：這是讓 Harness 具備移植性的唯一方法。

---
**由 CK's Pi Code Agent Harness 核心團隊維護。**
