# RATIONALE: JuliusBrussee/caveman 整合決策理由書

## 1. 決策背景
*   **來源專案**：https://github.com/JuliusBrussee/caveman
*   **核心功能**：超高壓縮率通訊模式與 Token 經濟管理（含 Wenyan 文言文模式、記憶檔案壓縮、自動化 Commit/Review）。
*   **評估日期**：2026-05-13

## 2. 戰略分析 (Technical SWOT/TOWS)
*   **S (優勢)**：目前最強大的 Token 節省方案，針對 CJK (中日韓) 語言有獨特的文言文壓縮優化。具備實體腳本進行背景壓縮。
*   **W (劣勢)**：包含多個 Python 與 Node 腳本，手動移植維護成本極高。
*   **O (機會)**：讓本地 LLM 使用者能顯著延長會話生命週期，減少因上下文爆量導致的當機。

根據 **v3.7 導則**，這屬於 **SO 策略區間**：功能具備極高互補性且結構標準。

## 3. 最終決策：🟢 Path 1 (原生映射 - 透過 Submodule)
理由如下：
1.  **維護性優先**：Caveman 是一個快速演進的生態系，透過子模組我們能第一時間獲得最新的「文言文壓縮」模型優化與安全性修復。
2.  **腳本依賴**：原專案包含 `caveman-compress.py` 等關鍵腳本，若採 Path 3 蒸餾，將難以保持腳本與 Prompt 的同步更新。
3.  **零污染**：將其移出 Core 目錄並轉向子模組，維持 Harness 倉庫的極簡。

## 4. 實施方案
*   **子模組路徑**：`external/caveman`
*   **對接範圍**：映射其 `skills/` 目錄下的所有 7 項核心技能。
*   **清理**：移除 `pi-skills/caveman` 的本地舊複本。

---
**本文件依據 DISTILLATION_GUIDE v3.7 規範存檔。**
