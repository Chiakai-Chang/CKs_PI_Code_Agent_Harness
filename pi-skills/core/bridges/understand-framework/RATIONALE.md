# RATIONALE: Understand-Anything 整合決策理由書

## 1. 決策背景
*   **來源專案**：https://github.com/mariozechner/understand-anything (移植版)
*   **核心功能**：專案全量代碼掃描、知識圖譜生成、架構級 Onboarding 導航。
*   **評估日期**：2026-05-13

## 2. 戰略分析 (Technical SWOT/TOWS)
*   **S (優勢)**：解決大型專案「代碼量大、結構複雜」導致 AI 難以入手的核心痛點。提供 AST 級別的邏輯連結而非單純全文檢索。
*   **W (劣勢)**：首次掃描較耗時，且會生成較大的 `knowledge-graph.json` 檔案。
*   **O (機會)**：建立本 Harness 的「結構解讀力」支柱，讓 Pi 具備秒讀數萬行代碼的 GPS 能力。

根據 **v3.7 導則**，這屬於 **SO 策略區間**：功能具備地基級重要性，是 AI 理解複雜專案的物理極限。

## 3. 最終決策：🟢 Path 3 (智慧蒸餾 - 核心人格化)
理由如下：
1.  **人格化對接**：我們將原本複雜的 CLI 掃描流程，重構為 Pi 易於理解的 `understand-onboard` 與 `understand-chat` 人格。
2.  **效能優化**：在蒸餾過程中，我們整合了「增量更新」與「過濾清單」，顯著降低了本地 LLM 的運算負擔。
3.  **架構深度**：保留了原專案對「知識圖譜」的定義，確保 Pi 獲取的架構數據具備工業級的保真度。

## 4. 實施方案
*   **路徑**：`pi-skills/core/understand/` 系列。
*   **核心人格**：
    *   `/understand`：生成知識圖譜。
    *   `/understand-onboard`：新專案快速導航。
    *   `/understand-chat`：基於圖譜的精準對話。

---
**本文件依據 DISTILLATION_GUIDE v3.7 規範存檔。**
