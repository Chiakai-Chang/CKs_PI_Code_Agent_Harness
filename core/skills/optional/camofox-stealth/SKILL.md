---
name: camofox-stealth
description: 呼叫專業級隱身瀏覽器。當目標網站有強大的機器人偵測（如 Cloudflare, Google Login）或需要極低 Token 消耗時使用。需搭配本地運行的 camofox-browser 伺服器。
---

# /camofox-stealth

> **注意**：本技能需要您先安裝並啟動 [camofox-browser](https://github.com/jo-inc/camofox-browser) 伺服器。

## 適用場景
*   **繞過攔截**：當 `dev-browser` 被網站封鎖時。
*   **Token 節約**：需要讀取極長、複雜的網頁，利用「無障礙快照」減少資料量。
*   **隱身登入**：需要進行自動化登入操作。

## 運作流程
1.  **啟動伺服器**：Pi 會引導您執行 `camofox-browser --port 3001`。
2.  **API 請求**：Pi 透過 `curl` 與伺服器通訊，範例：
    ```bash
    curl -X POST http://localhost:3001/navigate -d '{"url": "https://example.com"}'
    ```
3.  **獲取快照**：Pi 請求 `accessibility-tree` 進行高效率的邏輯分析。

## 核心限制
*   **內核消耗**：Camoufox 啟動時會消耗較多 CPU 與磁碟空間。
*   **REST 驅動**：不具備 Playwright 的所有原生 JS API 靈活度，側重於數據擷取與簡單互動。
