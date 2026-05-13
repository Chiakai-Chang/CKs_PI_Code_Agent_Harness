# RATIONALE: BayramAnnakov/claude-reflect 整合決策理由書

## 1. 決策背景
*   **來源專案**：https://github.com/BayramAnnakov/claude-reflect
*   **核心功能**：自我進化記憶系統（自動擷取對話中的使用者修正與偏好，並同步至專案規範）。
*   **評估日期**：2026-05-13

## 2. 戰略分析 (Technical TOWS)
*   **S (優勢)**：具備成熟的 Python 邏輯來處理語義去重、修正擷取與規則合成。
*   **W (劣勢)**：原始碼高度耦合 Claude Code 的插件系統路徑。
*   **O (機會)**：本專案急需「自動學習」能力來完善 HelloAGENTS 的閉環開發體驗。

根據 **v3.7 導則**，此情境屬於 **SO 策略區間**：這是本專案的「核心必爭之地」，應整合其最強大的記憶邏輯。

## 3. 最終決策：🟢 Path 3 (智慧蒸餾 - 改寫核心邏輯)
我們選擇提取其「智慧精華」而非直接引入 Submodule，理由如下：
1.  **架構契合度**：其核心是 Python 處理程序，易於「脫水」並重新適配到 Pi 的 `session_end` 事件中。
2.  **高保真移植**：我們保留其「修正偵測 (Capture) -> 語義合成 (Synthesize) -> 規範寫入 (Inject)」的完整流水線。
3.  **依賴成本低**：維持「零依賴」原則，不需強迫使用者安裝額外的插件管理工具。

## 4. 實施方案：hello-reflect (v2.0)
*   **形式**：將 `claude-reflect` 的核心演算法實作於 `pi-skills/core/hello-reflect/scripts/` 之下。
*   **運作邏輯**：當 Pi 完成一個 Session 時，自動觸發此腳本掃描歷史，尋找關鍵修正點並詢問使用者是否更新 `CLAUDE.md` 或 `AGENTS.md`。

---
**本文件依據 DISTILLATION_GUIDE v3.7 規範存檔，作為未來技術回溯之依據。**
