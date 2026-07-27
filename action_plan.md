# 🛣️ OmniHeal 行動路線圖 (Action Plan)

**專案**: CK's Pi Code Agent Harness (`CKs_PI_Code_Agent_Harness`)  
**治理框架**: C.A.S.E. Framework & OmniHeal Methodology  

---

## ⚡ 今日已完成修復 (Completed Today)

- [x] **[HIGH-PRIORITY] 修復 `taste-bridge` 抹除 SystemPrompt 之 Bug**
  - **位置**: [pi-extensions/taste-bridge/index.ts](file:///D:/MyProject/CKs_PI_Code_Agent_Harness/pi-extensions/taste-bridge/index.ts#L23-L29)
  - **處置**: 保留既有 `event.systemPrompt` 並進行拼接。

- [x] **[HIGH-PRIORITY] 修復 `yes-hooks-bridge` 灰牌自迴圈與標籤轉義 Bug**
  - **位置**: [pi-extensions/yes-hooks-bridge/index.ts](file:///D:/MyProject/CKs_PI_Code_Agent_Harness/pi-extensions/yes-hooks-bridge/index.ts#L158-L184)
  - **處置**: 訊息改用方括號 `[invoke]`, `[read-file]`, `[bash]` 防止正規表示式誤判；Strike 3 改為 `deliverAs: "followUp"` 人類斷路器。

- [x] **[MEDIUM-PRIORITY] 補全 `taste-bridge` 單元測試與 `package.json` ESM 聲明**
  - **位置**: [tests/test_taste_bridge.py](file:///D:/MyProject/CKs_PI_Code_Agent_Harness/tests/test_taste_bridge.py) / [pi-extensions/taste-bridge/package.json](file:///D:/MyProject/CKs_PI_Code_Agent_Harness/pi-extensions/taste-bridge/package.json)
  - **處置**: 增加契約測試斷言 `(event.systemPrompt ?? "")`，補上 `"type": "module"` 保持全專案一致。

- [x] **[LOW-PRIORITY] 複製 `OmniHeal` 至 `research/` 並確認隔離**
  - **位置**: [research/OmniHeal](file:///D:/MyProject/CKs_PI_Code_Agent_Harness/research/OmniHeal)
  - **處置**: 驗證 `.gitignore` 已包含 `research/`。

---

## 📅 本週建議優化 (This Week's Recommendations)

- [ ] **1. 自動化測試覆蓋率與 Bridge 契約測試持續強化**
  - **目標**: 對未來任何新建 Bridge Extension（如新新增 Hook 時），於 `scripts/verify-bridges.py` 中自動驗證 `event.systemPrompt` 疊加規範。

- [ ] **2. 定期執行 `python scripts/setup.py --mode restore` 驗證**
  - **目標**: 確保開發者在任何平台 checkout 乾淨倉庫時，能秒級自動還原 9 大橋接與全套合規組態。

---

## 💪 強項維持 (Strengths Maintained)

1. **嚴密的自動化測試防衛網**: 176 個 Python 單元測試 100% PASS，0 依賴標準庫即時跑完 (0.035s)。
2. **5 層閉環 Operating System**: 從 Layer 0 (YES.md / Namespace Guard) 到 Layer 4 (Evidence Gate / Darwin / Autonomous Experiment) 權責分明。
3. **C.A.S.E. 規格化狀態記憶**: `task_plan.md` 實體檔案結合 `compact-continuation-bridge`，上下文壓縮後仍能保持任務記憶與自動接續。
