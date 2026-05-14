# 🧠 決策紀錄 (Rationale) - KERNEL: Context Engineering (Passive Skill)

## 1. 為什麼要進行「內核級蒸餾」？
根據 `DISTILLATION_GUIDE.md`，我們對 `muratcankoylan/Agent-Skills-for-Context-Engineering` 採取了路徑 3 (Smart Refactor)。
這是一個「去理論化、重演算法」的蒸餾，理由如下：
*   **CP 值極高**：原始 Repo 包含大量學術背景與理論說明，直接搬運會造成嚴重的「資訊過載」。我們僅提取其核心「注意力管理演算法」與「資訊噪訊比優化規則」。
*   **解決底層痛點**：AI 在長對話中常見的「Lost-in-the-Middle」與「無效 Token 堆疊」是影響工程誠信的物理瓶頸。這套蒸餾規則能為 Pi 助手安裝一個「底層記憶體優化器」。
*   **與現有功能相容**：這套規則被定位為「被動技能」，它不干涉 `OMC` 的人格或 `AIxBDD` 的流程，而是作為這些功能的「傳輸協議」。

## 2. 蒸餾出的「內核協議」內容
我們提取了以下三項元知識：
1.  **Prefix-Stabilization (KV-Cache 穩定化)**：優化硬體快取命中率。
2.  **U-Curve Placement (注意力 U 型分配)**：確保關鍵目標不被「埋沒」。
3.  **Observation Masking (觀察值掩碼)**：將 80% 的無效 Token (Tool Outputs) 轉化為 5% 的精煉引用。

## 3. 未來的替代性與維護
*   **物理常數性質**：上下文管理是 Transformer 模型的物理特性，這些優化邏輯是「元知識」，不會隨模型更迭而失效。
*   **無痛替換**：優化規則被寫死在 `pi-rules/performance.md`。若未來有更好的模組，只需替換該文字區塊，無需修改任何程式碼或 Submodule。

## 4. 效益結論
*   **Token 節省**：預期在長對話中節省 20% - 40% 的無意義支出。
*   **成功率提升**：顯著降低 AI 因「資訊迷失」而導致的診斷錯誤。

---
**本文件依據 $docs/core/DISTILLATION_GUIDE.md 建立，標誌著本 Harness 具備了底層上下文自癒能力。**
