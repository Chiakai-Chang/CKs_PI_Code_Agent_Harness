# 🧠 決策紀錄 (Rationale) - Evolution Engine Bridge

## 1. 為什麼要引進 Evolver？
AI Agent 的主要瓶頸之一是「無法跨會話學習」。雖然我們有 `Hello Reflect` (海馬迴)，但它偏向短期記憶的微調。引進 `EvoMap/evolver` 是為了實現：
*   **長期基因優化**：透過 **GEP (Genome Evolution Protocol)**，將成功的開發路徑固化為「基因」，實現能力的遺傳。
*   **自動化錯誤模式識別**：主動掃描日誌，從「失敗」中提取「抗體」，防止 Agent 在同一塊石頭上絆倒兩次。
*   **底層自癒力**：讓開發環境具備生物般的進化能力。

## 2. 為什麼選擇「原生映射 (Native Mapping)」+「輕量橋接」？
根據 `DISTILLATION_GUIDE.md`：
*   **GEP 是標準**：Evolver 核心的基因 JSON 檔案是通用的能力協議。
*   **Submodule 確保更新**：我們引進其 `assets/gep/` 作為基因庫來源，確保 100% 享有上游針對新模型、新場景開發出的高效基因。
*   **環境解耦**：我們將其龐大的日誌分析腳本隔離在 `research/` 或 Submodule 中，而在 Bridge 層提供輕量化的指令入口。

## 3. 核心價值：演進力 (Evolutionary Power)
本 Bridge 將本 Harness 從「靜態配置」提升為「動態生命體」。它是 `PIP Guardian` 的後端大腦，負責將當下的修復行為轉化為永恆的開發紀律。

## 4. 維護計畫
*   定期同步 `external/evolver` 獲取最新的優化基因。
*   使用者可透過 `/evolve:save` 將自己的獨門秘籍「基因化」。

---
**本文件依據 $docs/core/DISTILLATION_GUIDE.md 建立，標誌著本 Harness 邁入「自我優化」新里程。**
