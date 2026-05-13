---
name: hello-reflect
description: 自動化反思系統。在 Session 結束時自動掃描對話紀錄，擷取使用者的修正建議與偏好，並協助將其轉化為持久的專案規範（如 CLAUDE.md）。
---

# /hello-reflect

> **蒸餾來源**：本功能的核心邏輯移植自 [BayramAnnakov/claude-reflect](https://github.com/BayramAnnakov/claude-reflect)。

## 核心功能
*   **自動偵測修正**：識別如 "no, do it this way" 或 "remember to X" 等關鍵語句。
*   **知識提煉**：利用 AI 去除冗餘，僅保留具備長期價值的開發規則。
*   **規範寫入**：自動更新專案根目錄的規範文件，確保下一次對話時 AI 能主動遵循。

## 使用方式
當您覺得當前的對話產生了值得紀錄的經驗時，可以直接呼叫：
> `/hello-reflect`

Pi 將會開始掃描當前會話並給出總結。

## 運作準則
*   **人工確認**：在更新任何檔案（如 CLAUDE.md）之前，必須先顯示差異並獲得使用者的確認。
*   **輕量執行**：使用內建 Python 腳本處理，確保執行速度快且不佔用過多記憶體。
