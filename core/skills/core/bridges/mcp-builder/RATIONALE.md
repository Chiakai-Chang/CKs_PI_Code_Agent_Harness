# RATIONALE: anthropics/skills/mcp-builder 整合決策理由書

## 1. 決策背景
*   **來源專案**：https://github.com/anthropics/skills (路徑: skills/mcp-builder)
*   **核心功能**：官方 Model Context Protocol (MCP) 伺服器建構引導技能。
*   **評估日期**：2026-05-13

## 2. 戰略分析 (Technical TOWS)
*   **S (優勢)**：Anthropic 官方定義的最佳實踐，對 AI 代理極度友好。
*   **O (機會)**：讓本 Harness 成為開發與部署 MCP 伺服器的首選框架。
*   **T (威脅)**：MCP 協議與 SDK 變動劇烈，手動維護成本極高。

根據 **v3.7 導則**，此情境屬於 **SO 策略區間**：功能強大且具備官方權威性。

## 3. 最終決策：🟢 Path 1 (原生映射 - 透過 Submodule)
我們選擇直接引用上游資產，理由如下：
1.  **維護性優先**：透過 `git submodule` 引入，只需 `update` 即可同步官方最新修正，避免一次性蒸餾導致的資訊過時。
2.  **架構契合度**：官方 `SKILL.md` 的 Markdown 格式與 Pi 的技能載入機制 100% 相容，無須重寫。
3.  **零重型依賴**：原專案僅為文檔與引導邏輯，不增加本專案的底層負擔。

## 4. 實施方案
*   **形式**：在 `external/anthropics-skills` 建立子模組。
*   **對接**：在 `pi-config/config.json` 中映射路徑：
    `{REPO_ROOT}/external/anthropics-skills/skills/mcp-builder`
*   **驗證**：在 Pi 中執行 `/mcp-builder` 確認引導流程正常啟動。

---
**本文件依據 DISTILLATION_GUIDE v3.7 規範存檔，作為未來技術回溯之依據。**
