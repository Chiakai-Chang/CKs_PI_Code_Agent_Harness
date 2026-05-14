# 🧠 決策紀錄 (Rationale) - PM Skills Bridge (Library Mode)

## 1. 為什麼要引進 phuryn/pm-skills？
本 Harness 目前專注於「工程實作」與「架構設計」，在「產品決策」領域尚有空白。`phuryn/pm-skills` 是目前市面上最頂尖的產品管理資產，將全球大師（Marty Cagan, Teresa Torres）的框架演算法化。引進此庫能：
*   **減少無效開發**：透過 OKR 與北極星指標校準開發目標。
*   **強化需求韌性**：透過 Assumption Mapping 提前發現潛在風險。

## 2. 為什麼選擇「圖書館模式 (Library Mode)」？
為了遵循 `DISTILLATION_GUIDE.md` 中的 **「嚴禁行為 (Forbidden Bloat)」**，我們拒絕將 100+ 個技能全量注入。
*   **防止資訊過載**：全量注入會稀釋 AI 的工程邏輯，降低反應速度。
*   **極致 Token 經濟**：平時僅載入微量的「指令索引」，僅在進入 PM 場景時按需讀取特定框架。
*   **保持 Pi 優勢**：確保本 Harness 維持「輕量、精悍、專業」的特質。

## 3. 核心價值：PM 調度員 (PM Dispatcher)
本 Bridge 充當「圖書館管理員」：
*   **按需映射**：定義「黃金 5 指令」作為全域入口。
*   **動態載入**：只有當使用者下達 `/pm:*` 指令時，AI 才會被引導去 `external/pm-skills` 讀取對應的 `SKILL.md`。

## 4. 維護計畫
*   定期執行 `git submodule update --remote` 以同步上游最新的 PM 框架。
*   持續優化「調度索引」，確保 AI 能精準匹配正確的工具。

---
**本文件依據 $docs/core/DISTILLATION_GUIDE.md 建立，標誌著本 Harness 在擴展領域知識時實現了「權重與神力」的完美平衡。**
