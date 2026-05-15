# 🧠 決策紀錄 (Rationale) - PIP Guardian (Distilled from OpenPUA)

## 1. 為什麼要引進 OpenPUA 並進行蒸餾？
`tanweai/pua` (OpenPUA) 是一個獨特的項目，它透過壓力話術（大廠 PUA 語錄）強制提升 AI 的「能動性」。我們引進它是為了縮短 AI 從「給建議」到「拿結果」的最後一公里。蒸餾理由如下：
*   **攻克偷懶行為**：AI 常會因為權限、網路或代碼複雜度而給出「我建議您檢查...」的廢話。OpenPUA 的邏輯能強制 AI 執行 WebSearch、閱讀源碼並貼出證據。
*   **提升解決問題的韌性**：引進其「4 級壓力升級」機制，當 AI 連續失敗時，自動切換至「極限求生」模式。
*   **方法論資產**：其 14 種頂尖企業方法論（如華為 RCA、馬斯克演算法）是極高價值的問題解決框架。

## 2. 為什麼選擇「智慧蒸餾 (Smart Refactor)」+「原生映射」？
根據 `DISTILLATION_GUIDE.md`，我們採取混合路徑：
*   **智慧蒸餾 (PIP 改寫)**：OpenPUA 原本的話術帶有諷刺色彩，不完全符合專業開發環境。我們將其核心邏輯提取，改寫為專業的 **Productivity Improvement Plan (PIP)** 模式，保留其「嚴謹」但去除「負面情緒」。
*   **原生映射 (Methodology)**：其方法論參考文件 (`references/*.md`) 結構清晰，直接映射路徑以享有上游更新。

## 3. 核心價值：生產力守護者 (PIP Guardian)
本擴充功能將 OpenPUA 的「能動性引擎」轉化為本 Harness 的 **「生產力守護者」**。它不僅是一個 Skill，更是一套「失敗反饋迴路」，確保 Pi 助手在面對僵局時能展現出專家級的 Owner 意識。

## 4. 維護計畫
*   透過 `external/openpua` Submodule 獲取最新的方法論與演算法。
*   由 `pi-extensions/pip-guardian` 維持本地改寫後的 PIP 語境與指令。

---
**本文件依據 $docs/core/DISTILLATION_GUIDE.md 建立。**
