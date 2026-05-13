# RATIONALE: nextlevelbuilder/ui-ux-pro-max-skill 整合決策理由書

## 1. 決策背景
*   **來源專案**：https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
*   **核心功能**：高階 UI/UX 設計智慧（含 161 種配色方案、67 種風格、57 組字體配對與 99 條設計準則）。
*   **評估日期**：2026-05-13

## 2. 戰略分析 (Technical SWOT/TOWS)
*   **S (優勢)**：擁有目前開源界最完整的 AI 設計數據庫，能顯著提升 AI 生成介面的美感與專業度。
*   **W (劣勢)**：數據龐大（CSV + Python 腳本），若採「脫水蒸餾」將喪失結構化搜尋的優勢。
*   **O (機會)**：讓本 Harness 從「程式碼助手」進化為「產品設計助手」。

根據 **v3.7 導則**，這屬於 **SO 策略區間**：功能具備極高戰略價值，且結構精密，應作為「旗艦級選配資產」進行整合。

## 3. 最終決策：🟢 Path 1 (原生映射 - 透過 Submodule)
理由如下：
1.  **高保真度**：原專案的強大在於其 `data/*.csv` 中的上百組配色與 `scripts/search.py` 的精準匹配邏輯。只有透過原生映射，Pi 才能 100% 調用這些底層數據庫，而非僅僅是幾行 Prompt。
2.  **維護性優先**：UI 設計趨勢變動快，透過子模組我們能第一時間獲取官方新增的風格（如 AI-Native UI）與配色，無需手動搬運數萬字數據。
3.  **依賴隔離**：我們將其定位為 **Optional (選配)**，並將龐大的數據庫保留在 `external/` 下，確保 Core 環境依然維持輕量。

## 4. 實施方案
*   **子模組路徑**：`external/ui-ux-pro-max-skill`
*   **對接範圍**：映射 `.claude/skills/` 下的所有 7 項設計技能：
    *   `ui-ux-pro-max`, `ui-styling`, `design`, `design-system`, `brand`, `slides`, `banner-design`
*   **環境補全**：更新 `restore.py` 以自動將這些「重型智慧」注入 Pi 的選配配置。

---
**本文件依據 DISTILLATION_GUIDE v3.7 規範存檔。**
