# RATIONALE: OthmanAdi/planning-with-files 整合決策理由書

## 1. 決策背景
*   **來源專案**：https://github.com/OthmanAdi/planning-with-files
*   **核心功能**：Manus-style 規劃系統（透過 task_plan.md, findings.md, progress.md 實現持久化記憶）。
*   **評估日期**：2026-05-13

## 2. 戰略分析 (Technical TOWS)
*   **S (優勢)**：解決 AI 「長對話失憶」的終極方案，支援會話恢復。
*   **W (劣勢)**：原專案更新頻率高，包含關鍵的安全防禦升級（防提示詞注入）。
*   **O (機會)**：本專案作為「本地 LLM 最佳伴侶」，必須具備極致的記憶持久性。

根據 **v3.7 導則**，此情境屬於 **SO 策略區間**：功能具備地基級重要性，且上游活躍。

## 3. 最終決策：🟢 Path 1 (原生映射) + 🟢 Path 2 (輕量橋接)
我們決定從原本的「智慧蒸餾 (Path 3)」升級為「原生映射」，理由如下：
1.  **安全性領先**：原專案 v2.21+ 引入了防提示詞注入邏輯，原生映射讓我們能第一時間獲取安全補丁。
2.  **維護性與同步**：透過 `git submodule` 引入，只需 `update` 即可享有上游所有功能進化，無需手動搬運。
3.  **橋接優化**：透過 `pi-extensions/planning-with-files-bridge` 進行輕量介入，解決全域絕對路徑定位問題。

## 4. 實施方案
*   **子模組路徑**：`external/planning-with-files`
*   **技能映射**：在 `pi-config/config.json` 中優先映射子模組路徑。
*   **穩定性兜底**：保留 `pi-skills/core/planning-with-files/` 作為經過本專案驗證的穩定快照。

---
**本文件依據 DISTILLATION_GUIDE v3.7 規範存檔。**
