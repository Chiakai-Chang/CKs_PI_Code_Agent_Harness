# 🧠 決策紀錄 (Rationale) - AIxBDD Bridge

## 1. 為什麼要引進 AIxBDD？
AIxBDD (AI-Driven Behavior-Driven Development) 由水球軟體學院開發，提供了一套極其嚴謹的 AI 工程化開發流程。它解決了以下核心問題：
*   **需求與實作的誠實性**：透過 `RED -> GREEN -> REFACTOR` 確保 AI 產出的程式碼完全符合規格。
*   **需求變更的韌性**：其 `aibdd-reconcile` 技能能有效處理開發過程中的需求調整，防止代碼腐化。
*   **高保真規格**：強調「事實發現 (Discovery)」先於「計畫 (Plan)」。

## 2. 為什麼選擇「原生映射 (Native Mapping)」路徑？
根據 `DISTILLATION_GUIDE.md`，我們選擇路徑 1 (Native Mapping)：
*   **SO 策略 (發揮優勢/利用機會)**：AIxBDD 的核心邏輯即為其高品質的技能 Markdown 檔案，結構與本專案高度相容。
*   **100% 享有上游更新**：透過 `git submodule` 掛載，我們可以隨時拉取最新版本的 AIxBDD 技能，無需手動同步副本。
*   **維護成本最低**：只需撰寫極簡的橋接配置（Bridge），即可讓 Pi 平台調用其神力。

## 3. 核心價值 (Core Value)
本 Bridge 將 AIxBDD 的「行為驅動」能力嫁接至 Pi 平台，與現有的 `SDD Pilot` (規格驅動) 形成互補，構建完整的自動化開發工廠。

## 4. 維護計畫
*   定期執行 `git submodule update --remote` 以同步最新技能。
*   若 AIxBDD 引入了新的工具依賴，由 `aixbdd-bridge` 進行能力補完。

---
**本文件依據 $docs/core/DISTILLATION_GUIDE.md 建立。**
