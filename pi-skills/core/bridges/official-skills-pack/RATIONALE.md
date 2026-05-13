# RATIONALE: Anthropic Official Skills (Selected) 整合決策理由書

## 1. 決策背景
*   **來源專案**：https://github.com/anthropics/skills
*   **核心功能**：包含 `frontend-design` (UI 開發), `webapp-testing` (網頁測試), `pdf/docx` (文件處理) 等官方高品質技能。
*   **評估日期**：2026-05-13

## 2. 戰略分析 (Technical SWOT/TOWS)
*   **S (優勢)**：官方維護，Prompt 品質極高，且專為 Agent 工作流設計。
*   **W (劣勢)**：部分技能（如 `skill-creator`）與 Pi 內建功能重複。
*   **O (機會)**：讓 Pi 獲得專業的 UI 設計與測試能力，補完開發全生命週期。
*   **T (威脅)**：無明顯威脅，屬純加強型資產。

根據 **v3.7 導則**，這屬於 **SO 策略區間**：利用官方高品質資產快速提升本 Harness 的基礎戰力。

## 3. 最終決策：🟢 Path 1 (原生映射 - 核心選集)
我們不採取「蒸餾」，而是直接「映射」選集，理由如下：
1.  **維護性**：官方 Skills 會隨協議演進，原生映射最省力。
2.  **避免臃腫**：我們不映射整個倉庫，僅挑選「對開發者最有價值」的項目。
3.  **靈魂保真**：官方的 SOP 流程非常完整，不應進行刪減。

## 4. 實施清單 (Selected Skills)
1.  **frontend-design**：智慧 UI 開發流程。
2.  **webapp-testing**：自動化 Web 測試指引。
3.  **pdf / docx**：增強對專案原始文件的閱讀能力。
4.  **skill-creator**：映射上游版本，作為內建版之參考/備援。

---
**本文件依據 DISTILLATION_GUIDE v3.7 規範存檔。**
