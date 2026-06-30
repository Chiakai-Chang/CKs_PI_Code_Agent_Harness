# RATIONALE: affaan-m/ECC 整合決策理由書

## 1. 決策背景
*   **來源專案**：https://github.com/affaan-m/ECC
*   **核心功能**：AI 開發全方位自動化掛鉤 (Hooks) 與超過 50 個專業代理人 (Agents)。
*   **評估日期**：2026-05-13

## 2. 戰略分析 (Technical SWOT/TOWS)
*   **S (優勢)**：目前最強大的 AI 紀律執行系統，能攔截語法錯誤與安全金鑰洩漏。
*   **W (劣勢)**：原專案高度耦合特定插件 API，直接移植代碼極其困難（High Friction）。
*   **O (機會)**：將其作為本 Harness 的底層「安全網」，讓 Pi 達到工業級的交付品質。

根據 **v3.7 導則**，這屬於 **SO 策略區間**：功能具備不可替代的戰略價值。

## 3. 最終決策：🟢 Path 1 (原生映射 - Agents) + 🟢 Path 2 (輕量橋接 - Hooks)
我們拒絕進行「一次性改寫 (Path 3)」，選擇了目前技術複雜度最高但維護回報最大的整合方案：
1.  **維護性優先**：ECC 的安全規範（如新的防禦 Regex）更新頻繁。透過 Submodule 引入，我們能隨時同步官方的「安全防火牆」。
2.  **避免功能殘廢**：原專案腳本間依賴複雜。我們透過開發 `pi-extensions/ecc-hooks-bridge` 建立翻譯層，保留了 100% 的原始檢查能力。
3.  **絕對路徑解決方案**：透過橋接器注入 `PI_HARNESS_ROOT` 絕對路徑，徹底解決了 Pi 在全域啟動時找不到子模組腳本的頑疾。

## 4. 實施方案：ECC Hooks Bridge
*   **形式**：建立專屬的 TypeScript Extension (`ecc-hooks-bridge`)。
*   **對接範圍**：映射 `external/everything-claude-code` 內的所有 Agents 與核心 Hooks。
*   **聯動**：在 Pi 的 `session_start` 與 `turn_end` 等關鍵事件中自動觸發 ECC 檢查邏輯。

---
**本文件依據 DISTILLATION_GUIDE v3.7 規範存檔，作為本專案鎮店之寶的技術脈絡依據。**
