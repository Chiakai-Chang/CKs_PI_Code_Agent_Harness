# RATIONALE: alchaincyf/nuwa-skill 整合決策理由書

## 1. 決策背景
*   **來源專案**：https://github.com/alchaincyf/nuwa-skill
*   **核心功能**：高維度認知提取引擎（將名人心智模型、決策啟發式、表達 DNA 轉化為可執行的 Skill）。
*   **評估日期**：2026-05-13

## 2. 戰略分析 (Technical SWOT/TOWS)
*   **S (優勢)**：目前業界唯一將「人格模仿」提升至「認知作業系統提取」深度的框架。具備 6 路並行 Agent 採集與 Darwin 自動化驗證機制。
*   **O (機會)**：讓本 Harness 具備「專家工廠」能力，可自產 Linus Torvalds 或 Andrej Karpathy 等頂級專家的數位分身進行 Code Review。
*   **T (威脅)**：認知提取的方法論演進極快，且高度依賴底層 Python 輔助腳本（清洗、轉錄）。

根據 **v3.7 導則**，這屬於 **SO 策略區間**：功能具備革命性價值，且結構精密，應採原生映射以確保引擎的完整性。

## 3. 最終決策：🟢 Path 1 (原生映射 - 引擎 + 案例集)
理由如下：
1.  **引擎保真度**：原專案包含複雜的 Python 多代理協作邏輯。若採 Path 3 蒸餾，將導致自動化採集與驗證功能「殘廢」。
2.  **維護性優先**：透過 Submodule 映射，只需 `update` 即可獲得作者對最新 AI 人物（如 R1/O1 時代的新思想家）的預蒸餾 Skill 案例。
3.  **案例價值**：內建的 13 位名家 Skill 是極佳的推理範本，對提升 Pi 的整體智力有顯著幫助。

## 4. 實施方案
*   **子模組路徑**：`external/nuwa-skill`
*   **映射範圍**：
    *   主指令：`external/nuwa-skill/SKILL.md` (huashu-nuwa)
    *   案例集：`external/nuwa-skill/examples/` 中的精選人物。
*   **自動化**：更新 `restore.py` 以確保 Pi 具備執行子模組內 Python 腳本的權限與正確路徑。

---
**本文件依據 DISTILLATION_GUIDE v3.7 規範存檔。**
