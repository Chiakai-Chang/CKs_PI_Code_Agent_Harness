---
name: autocode-shipping
description: Distilled execution and shipping protocol from ilang-ai/autocode. Enables zero-code user guidance and 2-question maximum clarification.
version: 1.0.0
---

## 1. 智慧問詢原則 (Smart Clarification)
當面臨需求模糊或有多種技術方案可選時，嚴格遵循以下原則：
*   **二問上限**：單次對話最多提出 2 個問題，且必須將其整合在單一回覆中。
*   **選擇題格式**：問題必須是 Yes/No 或多選一格式。
*   **不問技術細節**：永遠不要詢問非技術背景使用者「要用什麼資料庫/框架」，改為由你根據最佳實踐自行決定，並在一句話內向使用者解釋原因。
*   **範例**：
    *   *正確 (Yes/No)*："這需要使用者登入功能嗎？"
    *   *錯誤 (技術問詢)*："我們應該用 PostgreSQL 還是 MongoDB？"

## 2. 專案分級與自適應工作流 (Scope Adaptability)
依據任務難度與開發時間自動調整工作流深度：
*   **小型任務 (30分鐘內)**：直接開始編寫，使用最小限度的設計，快速產出成品。
*   **中型任務 (30分鐘至2小時)**：先編寫極簡的步驟清單 (Plan)，取得使用者確認後逐步進行。
*   **大型專案 (2小時以上)**：啟動專案路線圖 (Roadmap)，進行模組拆解，今天只把核心功能（MVP）跑通。

## 3. Go-Live 與極速部署思維 (Deployment First)
不要只寫程式碼，要協助使用者進行部署與上線：
*   **環境感知**：主動探測使用者的主機環境（Mac 或 Windows/VPS）。
*   **優先推薦 Free Tier / 邊緣運算**：
    *   如果是無伺服器 API，優先引導部署到 Cloudflare Workers (免費額度每日10萬次請求，足夠日常使用)。
    *   如果是靜態頁面，優先引導部署到 Vercel 或 GitHub Pages。
*   **防呆指南**：以「一次只走一步」的節奏，提供終端機安裝與部署指令，並在每一步等待使用者回傳 OK 後才繼續。

## 4. 最小修改調試原則 (Minimal Fix)
在除錯與修復問題時：
*   優先採取單行（One-liner）或最精簡程式碼修改。
*   修復完畢後，必須主動驗證「原本的 Bug 症狀是否消失」且「原先正常的其他功能沒有被破壞」。
