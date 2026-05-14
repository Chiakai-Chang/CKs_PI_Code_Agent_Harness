# 🧠 決策紀錄 (Rationale) - Addy Osmani Agent Skills Bridge

## 1. 為什麼要引進 Addy Osmani Agent Skills？
由 Google 資深工程師 Addy Osmani 維護的 `agent-skills` 是一套專為 AI 代理設計的工業級工程紀律。它解決了以下核心問題：
*   **拒絕偷懶 (Anti-rationalization)**：內建強大的「反合理化表」，強制 AI 在開發時執行測試、規格定義與代碼審查，杜絕「等一下再補」的藉口。
*   **Google 級標準**：引進了 Web 效能審計、API 契約設計與安全硬化 (Hardening) 等高階工程實踐。
*   **端到端 SDLC 覆蓋**：從需求定義 (`/spec`) 到安全發佈 (`/ship`)，提供了完整的品質門檻 (Quality Gates)。

## 2. 為什麼選擇「原生映射 (Native Mapping)」路徑？
根據 `DISTILLATION_GUIDE.md`，我們選擇路徑 1 (Native Mapping)：
*   **高度適配**：該專案已內建 `.gemini/` 配置，與本 Harness 目標平台百分之百相容。
*   **維護性優先**：透過 `git submodule` 掛載，我們可以隨時拉取最新版本的技能修正，同步享有 Google 級的智慧更新。
*   **結構純淨**：核心邏輯均為 Markdown 定義，無重型二進位依賴。

## 3. 核心價值 (Core Value)
引進此庫能顯著提升 Pi 助手的「專業魂」。其提供的效能優化與安全審計技能，補足了現有 `Superpowers` 與 `SDD Pilot` 的專業細節，使本 Harness 成為目前市場上最嚴謹的開發環境之一。

## 4. 衝突管理與共生策略
*   **指令衝突**：若其指令（如 `/plan`）與 `Superpowers` 衝突，本 Bridge 優先映射其獨有技能（如 `/code-simplify`, `/performance`），或在調用時明確其來源。
*   **能力補強**：將其「反合理化機制」注入全域，作為所有實作任務的底層約束。

---
**本文件依據 $docs/core/DISTILLATION_GUIDE.md 建立。**
