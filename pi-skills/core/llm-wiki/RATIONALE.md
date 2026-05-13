# RATIONALE: praneybehl/llm-wiki-plugin 整合決策理由書

## 1. 決策背景
*   **來源專案**：https://github.com/praneybehl/llm-wiki-plugin
*   **核心功能**：Andrej Karpathy 提出的 LLM Wiki 模式（將原始資訊編譯為結構化維基，支援圖譜、BM25 搜尋與結構檢查）。
*   **評估日期**：2026-05-13

## 2. 戰略分析 (Technical TOWS)
*   **S (優勢)**：高品質的 Python 輕量腳本（搜尋、Lint、統計），零依賴，格式與 Obsidian 相容。
*   **O (機會)**：將 Pi 的角色從「代碼執行者」提升至「專案知識管理員」，實現知識複利成長。
*   **T (威脅)**：手動維護大規模 Markdown 連結極其困難，原專案提供的自動化 Lint 是核心護城河。

根據 **v3.7 導則**，此情境屬於 **SO 策略區間**：功能強大且具備獨特的戰略地位，應完整保留其靈魂。

## 3. 最終決策：🟢 Path 1 (原生映射 - 透過 Submodule)
理由如下：
1.  **維護性優先**：LLM Wiki 模式與搜尋演算法仍在快速演進，透過子模組直接對接，能隨時更新官方最優化的 Lint 規則。
2.  **架構契合度**：原專案結構與 Pi 的 Skills 系統高度一致，不需改寫代碼即可運作。
3.  **零重型依賴**：完全基於 Python 標準庫，符合本專案的輕量化初衷。

## 4. 實施方案
*   **子模組路徑**：`external/llm-wiki-plugin`
*   **對接**：在 `pi-config/config.json` 中映射路徑：
    `{REPO_ROOT}/external/llm-wiki-plugin/skills/llm-wiki`
*   **地位**：作為「專案大腦層」的核心資產。

---
**本文件依據 DISTILLATION_GUIDE v3.7 規範存檔。**
