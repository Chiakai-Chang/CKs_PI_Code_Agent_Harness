---
name: hello-reflect
description: 自動化反思系統。在 Session 結束時自動掃描對話紀錄，擷取使用者的修正建議與偏好，並協助將其轉化為持久的專案規範（如 CLAUDE.md、.agents/AGENTS.md）。
---

# /hello-reflect

> **蒸餾來源**：本功能的核心邏輯移植自 [BayramAnnakov/claude-reflect](https://github.com/BayramAnnakov/claude-reflect)。

## 核心功能
*   **自動偵測修正**：識別如 "no, do it this way" 或 "remember to X" 等關鍵語句。
*   **知識提煉**：利用 AI 去除冗餘，僅保留具備長期價值的開發規則。
*   **規範寫入**：自動更新專案的規範文件（如 `CLAUDE.md` 或 `.agents/AGENTS.md`）。

## 運作流程 (SOP)

1.  **環境定位**：
    *   獲取本專案根目錄路徑。
    *   確定當前 Pi Session 的 JSONL 檔案路徑（通常在 `~/.pi/agent/sessions/`）。

2.  **執行擷取**：
    *   執行以下指令（路徑已由 Harness 自動注入）：
        ```bash
        python "{PI_HARNESS_ROOT}/pi-skills/core/hello-reflect/scripts/capture.py" "{SESSION_FILE}"
        ```
    *   分析輸出的 JSON 學習點。

3.  **語義總結與同步**：
    *   讀取現有的規範文件（如 `CLAUDE.md` 或 `.agents/AGENTS.md`）。
    *   將新擷取的學習點與現有規則合併。
    *   **知識轉移 (Wiki-Sync)**：如果學習點屬於「業務邏輯」或「架構知識」，引導使用者使用 `/llm-wiki` 進行永久存檔。
    *   使用 AI 人格進行「脫水」與「去重」。

4.  **用戶確認**：
    *   顯示預計更新的規範文件內容。
    *   詢問使用者：「是否確認更新開發規範？（例如更新 CLAUDE.md 或 .agents/AGENTS.md，並建議同步更新至 LLM Wiki 以利長期沉澱）」

## 運作準則
*   **高保真**：保留使用者原始修正的核心意圖。
*   **輕量執行**：使用內建 Python 腳本處理，確保執行速度快。
*   **人工確認**：禁止在未獲授權前擅自修改專案規範檔案。


