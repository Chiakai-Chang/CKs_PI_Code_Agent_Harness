# RATIONALE: mattpocock/skills 整合決策理由書

## 1. 決策背景
*   **來源專案**：https://github.com/mattpocock/skills
*   **核心功能**：由 TypeScript 大師 Matt Pocock 打造的高品質開發者工作流（Diagnose, Zoom-out, Improve Architecture）。
*   **評估日期**：2026-05-13

## 2. 戰略分析 (Technical SWOT/TOWS)
*   **S (優勢)**：大師級的 TypeScript 見解，專門解決「宏觀架構 (Macro Architecture)」與「深度偵錯 (Deep Diagnose)」問題。
*   **W (劣勢)**：部分功能（如 TDD）與 Superpowers 重疊。
*   **O (機會)**：強化 Pi 在處理複雜 TypeScript/JavaScript 專案時的專業深度，特別是在架構優化方面。

根據 **v3.7 導則**，這屬於 **SO 策略區間**：利用專家級資產補完本 Harness 在特定語言（TS/JS）上的天花板。

## 3. 最終決策：🟢 Path 1 (原生映射 - 精選)
理由如下：
1.  **維護性優先**：TypeScript 演進極快，Matt 會持續更新其 Skills 以適應最新語法，直接 Submodule 映射是最省力的方案。
2.  **獨特性**：`/zoom-out` 與 `/improve-codebase-architecture` 提供了目前其他框架少有的「架構級視角」，極具補完價值。
3.  **零污染**：放置於 `external/` 隔離區，不影響 Core Skills 的精簡度。

## 4. 實施清單 (Curated Selection)
我們挑選了最具差異化價值的技能進行映射：
1.  **zoom-out**：宏觀架構解讀（GPS 視角）。
2.  **improve-codebase-architecture**：尋找並實施架構優化（深模組化）。
3.  **diagnose**：深入的 Bug 根因分析。
4.  **grill-with-docs**：配合文檔進行技術對練（新 API 學習）。
5.  **handoff**：產出高品質的開發交接文檔。

---
**本文件依據 DISTILLATION_GUIDE v3.7 規範存檔。**
