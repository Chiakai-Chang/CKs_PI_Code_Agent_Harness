# RATIONALE: cli-printing-press 模式蒸餾理由書

## 1. 決策背景
*   **來源專案**：https://github.com/mvanhorn/cli-printing-press
*   **核心功能**：Agent-Native CLI 設計準則（Token 壓縮輸出、類型化退出碼、自動 JSON 切換）。
*   **評估日期**：2026-05-13

## 2. 戰略分析 (Technical TOWS)
*   **S (優勢)**：具備工業級的 Token 節省與 Agent 容錯設計，能顯著降低輸入端 Token。
*   **W (劣勢)**：原專案為 Go 語言且體積龐大，直接整合會引入重型編譯環境。
*   **O (機會)**：將其模式「蒸餾」為本專案的開發規範，提升所有自研腳本與 MCP 伺服器的品質。

根據 **v3.7 導則**，此情境屬於 **WO 策略區間**：功能有價值但代價太高。我們採 **🟢 Path 3 (智慧蒸餾 - 提取模式)**，徹底消滅弱點，只保留智慧。

## 3. 最終決策：🟢 Path 3 (模式蒸餾)
理由如下：
1.  **零依賴原則**：我們不需要 Go 語言環境，只需要其「設計思想」。
2.  **相輔相成**：其「數據層優化」與 `caveman` 的「語言層優化」完美聯手，實現全鏈路 Token 經濟。
3.  **架構升級**：將其轉化為 `pi-rules` 中的強制規範，確保 Harness 產出的所有工具都具備頂級 AI 適應力。

## 4. 實施方案：Agent-Native CLI Spec
*   **規範化**：在 `pi-rules/cli-standards.md` 定義輸出的 `--compact` 與 `--select` 標準。
*   **對接**：在 `mcp-builder` 技能中注入這些模式，引導 Pi 在開發新工具時自動遵循。
*   **錯誤碼**：實施「類型化退出碼」，讓 `ecc-hooks-bridge` 具備更強的偵錯力。

---
**本文件依據 DISTILLATION_GUIDE v3.7 規範存檔。**
