# 🧠 決策紀錄 (Rationale) - OMC Agent Factory Bridge

## 1. 為什麼要引進 oh-my-claudecode (OMC)？
OMC 是目前多代理編排領域的「智慧上游」。它不僅是一組技能，更是一套成熟的 **「AI 團隊作戰系統」**。整合理由如下：
*   **最強代理矩陣**：定義了 32+ 種專業代理人格（如 `sisyphus` 持久化引擎、`oracle` 全知架構師），其定義嚴謹度為目前社群最高。
*   **Sisyphus 永不放棄精神**：其核心的「驗證-修復」自動化循環，能有效解決 AI 遇到環境配置失敗或測試挫折時的放棄傾向。
*   **Team Mode 流水線**：提供標準化的「計畫 -> PRD -> 執行 -> 驗證」工程閉環，將 AI 從對話框提升為生產線。

## 2. 為什麼選擇「原生映射 (Native Mapping)」路徑？
根據 `DISTILLATION_GUIDE.md`，我們選擇路徑 1 (Native Mapping)：
*   **編排發源地**：OMC 是多代理邏輯的誕生地，直接 Submodule 確保我們能 100% 享有最新代理定義的更新。
*   **結構高度相容**：OMC 的 `agents/` 與 `skills/` 目錄均採高品質 Markdown 格式，與本 Harness 的「專家大腦」架構天然適配。
*   **戰略互補**：它補足了 `Superpowers` 在長程執行與大規模團隊協作上的短板。

## 3. 核心價值：代理工廠 (Agent Factory)
本 Bridge 將 OMC 轉化為本 Harness 的 **「代理工廠」**。使用者不再受限於單一 AI 助手，而是隨時能透過指令召喚一個由架構師、執行者與驗證師組成的專門團隊。

## 4. 維護計畫
*   定期執行 `git submodule update --remote` 以拉取最新的代理人格與編排邏輯。
*   對於依賴 tmux 的並行能力，在 Pi 平台提供優雅降級或專屬橋接。

---
**本文件依據 $docs/core/DISTILLATION_GUIDE.md 建立。**
