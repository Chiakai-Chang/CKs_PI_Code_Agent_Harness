# RATIONALE: jo-inc/camofox-browser 整合決策理由書

## 1. 決策背景
*   **來源專案**：https://github.com/jo-inc/camofox-browser
*   **核心功能**：針對 AI Agent 優化的隱身瀏覽器 (C++ 級指紋偽裝、無障礙樹快照)。
*   **評估日期**：2026-05-13

## 2. 戰略分析 (Technical TOWS)
*   **S (優勢)**：目前最強的反偵測能力，能繞過 Cloudflare/Akamai；節省 90% Token 的快照技術。
*   **W (劣勢)**：依賴特定的 Firefox 內核 (Camoufox)，安裝體積較大。
*   **O (機會)**：讓 Pi 成為具備「專業爬蟲/驗證」能力的頂級 Agent。

根據 **v3.7 導則**，此情境屬於 **ST 策略區間**：我們渴望其頂尖的隱身力，但必須透過橋接來隔離其龐大的內核依賴，保持專案核心的輕量。

## 3. 最終決策：🟢 Path 2 (輕量橋接 - 作為進階選配)
理由如下：
1.  **能力互補**：現有 `dev-browser` 易被攔截，Camofox 提供「降維打擊」的替代方案。
2.  **嚴禁臃腫**：我們不將 Camoufox 內核內建，而是透過「引導式安裝」將其定位為可選的外掛。
3.  **零依賴開發**：Pi 僅透過 `curl` 指令調用其 REST API，維持本 Harness 倉庫的純淨度。

## 4. 實施方案：camofox-stealth
*   **形式**：在 `pi-skills/optional/camofox` 中提供連線範本。
*   **運作邏輯**：Pi 作為客戶端，調用用戶本地啟動的 `camofox-browser` 伺服器。
*   **聯動**：在 `browser-expert` 代理中注入選型邏輯（簡單網頁用 dev-browser，難搞網站用 camofox）。

## 5. 升級與釘版 (2026-07-08)
*   **釘版**：後端釘 `@askjo/camofox-browser@1.11.2`（記於 `pi-config/harness-config.json`），skill 對準此版 `/tabs`+snapshot API，杜絕 `npx latest` 移動標的與既有 `3001`/`/navigate` 漂移。
*   **更新流**：後端升級＝改 `harness-config.json` 版本後重跑 `setup.py`；harness 其餘更新照 `git pull` → `setup.py --mode restore` → `pi update` 單一路徑。
*   **生命週期**：`recon.sh` detached 啟動 + pidfile + health-check，解決 Windows/Git Bash 短命 tool-call 背景進程問題。

---
**本文件依據 DISTILLATION_GUIDE v3.7 規範存檔。**
