# RATIONALE: obra/superpowers 整合決策理由書

## 1. 決策背景
*   **來源專案**：https://github.com/obra/superpowers
*   **核心功能**：為 AI Agent 定義的一套嚴謹開發方法論（含 TDD、系統化規劃、子代理管理）。
*   **評估日期**：2026-05-13

## 2. 戰略分析 (Technical SWOT/TOWS)
*   **S (優勢)**：目前業界最嚴謹的 AI 工程紀律框架，將 AI 從「代碼生成器」轉化為「工程師」。
*   **W (劣勢)**：對話輪數較多，Token 消耗量較原生開發大。
*   **O (機會)**：本專案已有大部分 Skills，但分散且難以同步上游的最新修正。
*   **T (威脅)**：AI 代理的開發 SOP 正在快速演進。

根據 **v3.7 導則**，這屬於 **SO 策略區間**：功能強大且結構完美，應作為本 Harness 的「靈魂準則」進行整合。

## 3. 最終決策：🟢 Path 1 (原生映射 - 透過 Submodule)
我們決定從原本的「分散蒸餾 (Path 3)」升級為「原生映射」，理由如下：
1.  **維護性優先**：Superpowers 是一個活躍的框架，透過子模組直接對接，只需一個 `git submodule update` 即可獲得最新版的人格修訂（如更強的 TDD 邏輯）。
2.  **架構契合度**：該專案本就是 Markdown 技能包的集合，與 Pi 的 Skills 加載機制完美匹配。
3.  **零資產流失**：子模組保留了完整的 `references/` 與 `scripts/`，這是在分散蒸餾時最容易遺漏的高價值資產。

## 4. 實施方案
*   **子模組路徑**：`external/superpowers`
*   **映射策略**：在 `pi-config/config.json` 中映射子模組的 `skills/` 目錄。
*   **優先級**：將 `using-superpowers` 設為入口技能。

---
**本文件依據 DISTILLATION_GUIDE v3.7 規範存檔。**
