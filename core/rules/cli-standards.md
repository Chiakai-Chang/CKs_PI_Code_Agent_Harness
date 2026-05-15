# 🏗️ Agent-Native CLI 設計標準 (CK-Spec-01)

> **蒸餾來源**：本標準部分參考自 `mvanhorn/cli-printing-press` 的工業級實踐。

本專案開發的所有 CLI 腳本、Helper 與 MCP 伺服器必須遵循以下標準，以最大化 AI 處理效率。

## 1. 輸出優化 (Output Standards)

### A. `--compact` 模式 (強制實作)
*   **定義**：當啟用此 flag 時，僅輸出 AI 執行決策所需的關鍵數據。
*   **行為**：移除裝飾性文字、日期格式化、長描述等。
*   **範例**：
    *   *Normal*: `ID: 101 | Name: Users | Created: 2024-01-01 | Size: 45MB | Description: This is a system table...`
    *   *Compact*: `{"id":101,"name":"Users","size":45}`

### B. `--select` 旗標
*   **定義**：允許調用者（AI 或腳本）精確選擇需要的欄位，減少數據傳輸量。
*   **行為**：接收逗號分隔的字串，僅過濾該屬性輸出。

### C. 自動 JSON 切換 (Auto-JSON)
*   **邏輯**：如果 `stdout` 不是終端機 (isatty is False)，預設切換為 JSON 格式，方便下一個管道或 AI 直接解析。

## 2. 錯誤處理 (Actionable Errors)

### A. 類型化退出碼 (Typed Exit Codes)
禁止全量使用 `exit(1)`。請遵循以下擴充錯誤碼，讓 AI 能根據退出碼自動重試：
*   **0**：成功 (Success)
*   **3**：資源未找到 (Not Found) - AI 應檢查路徑或 ID。
*   **4**：參數錯誤 (Validation Error) - AI 應檢查指令參數。
*   **7**：觸發限流 (Rate Limited) - AI 應等待或重試。
*   **9**：權限不足 (Permission Denied) - AI 應向用戶申請提權。

### B. 明確的修復建議
當發生錯誤時，Stderr 應包含一行的「可執行建議」。
*   *壞例子*: `File Error`
*   *好例子*: `ERROR: file not found. Check if /src/index.ts exists.`

## 3. 性能紀律
*   **秒級響應**：所有 Helper 腳本的啟動時間應低於 200ms。
*   **零副作用偵測**：提供 `--dry-run` 以供 AI 在執行危險操作（如刪除、重構）前進行模擬。
