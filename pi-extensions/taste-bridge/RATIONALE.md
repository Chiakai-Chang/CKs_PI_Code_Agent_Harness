# 🧠 決策紀錄 (Rationale) - Taste Engine Bridge

## 1. 為什麼要引進 Taste-Skill？
AI 在生成前端代碼時，極容易陷入「罐頭感 (Generic Slop)」的陷阱：使用純黑背景、AI 紫色漸變、Inter 字體以及缺乏層次感的 3 欄卡片佈局。整合 `taste-skill` 理由如下：
*   **拒絕低階審美**：透過強制性的「反 AI 慣性 (Anti-Slop)」規則，禁止常見的 AI 設計錯誤，提升產出物的高級感。
*   **參數化控制**：引入「設計三旋鈕 (The Three Dials)」概念，將主觀的品味轉化為可量化的設計變異度、動態強度與視覺密度。
*   **極致前端工程**：強調 CSS 硬體加速、Viewport 穩定性 (`100dvh`) 與 Framer Motion 的物理模擬，確保 UI 不僅美觀且性能卓越。

## 2. 為什麼選擇「原生映射 (Native Mapping)」路徑？
根據 `DISTILLATION_GUIDE.md`，我們選擇路徑 1 (Native Mapping)：
*   **純淨資產**：該 Repo 的核心是高品質的 Markdown 技能定義，與本 Harness 的架構完全相容。
*   **持續進化**：作者正深入研究 AI Laziness（偷懶行為）的根因與對策，Submodule 確保我們能即時獲得這些「反偷懶」的最新研究成果。
*   **零維護負擔**：無需手動維護副本，只需極簡的橋接配置。

## 3. 核心價值：視覺指揮官 (Visual Commander)
本 Bridge 為本 Harness 注入了「審美大腦」。它讓 Pi 助手從一個單純的「寫碼機」進化為具備「設計直覺」的資深工程師。

## 4. 維護計畫
*   定期執行 `git submodule update --remote` 以同步最新的設計模式與 AI 心理研究成果。
*   由 `taste-bridge` 負責將設計參數注入全域 Session 上下文。

---
**本文件依據 $docs/core/DISTILLATION_GUIDE.md 建立。**
