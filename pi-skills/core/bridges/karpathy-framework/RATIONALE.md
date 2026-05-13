# RATIONALE: forrestchang/andrej-karpathy-skills 整合決策理由書

## 1. 決策背景
*   **來源專案**：https://github.com/forrestchang/andrej-karpathy-skills
*   **核心功能**：基於 Andrej Karpathy 觀察的 AI 開發準則（先思考、簡約至上、精確修改、目標驅動）。
*   **評估日期**：2026-05-13

## 2. 戰略分析 (Technical SWOT/TOWS)
*   **S (優勢)**：目前公認最能有效防止 LLM 「過度工程化」與「草率修補」的行為準則。
*   **W (劣勢)**：原專案規模較小，主要由單個核心 Skill 組成。
*   **O (機會)**：本專案已內建其快照，但改採子模組可獲得更完整的 `EXAMPLES.md` 等輔助學習資料。
*   **T (威脅)**：若 AI 行為準則更新，手動快照將失去及時性。

根據 **v3.7 導則**，這屬於 **SO 策略區間**：雖然本專案已有實體檔案，但為了「高保真」與「維護性」，應升級為子模組映射。

## 3. 最終決策：🟢 Path 1 (原生映射 - 透過 Submodule)
理由如下：
1.  **維護性優先**：雖然內容相對穩定，但上游專案的 `EXAMPLES.md` 會持續增加新的誤用案例對比，這些對 AI 的微調推理極具價值。
2.  **架構契合度**：完全符合 Agent Skills 標準，不需任何改寫。
3.  **零污染**：將其移出 Core 目錄並轉向子模組，能進一步精簡 Harness 本體的檔案大小。

## 4. 實施方案
*   **子模組路徑**：`external/karpathy-skills`
*   **映射路徑**：`external/karpathy-skills/skills/karpathy-guidelines`
*   **清理**：移除 `pi-skills/core/karpathy-guidelines` 的本地複本。

---
**本文件依據 DISTILLATION_GUIDE v3.7 規範存檔。**
