# 收穫二：有界執行與空轉偵測 — 防止無限循環的自治任務

> 來源：pi-until-done 的 agent_settled hook 狀態機、turn budget、spin guard。
> 對應本專案：compact-continuation-bridge 處理 session 延續但無預算限制與空轉保護。

## pi-until-done 的設計

**核心機制**：`agent_settled` hook 擁有自動延續決定權，每次 agent 回合結束時執行完整的狀態轉換檢查。

### 狀態轉換邏輯（handleEndTransitions）
```
if turnsUsed >= maxTurns → handleBudgetExhausted (預算耗盡，停止)
else if userMessagedThisTurn → 記錄 continue verdict，不延續 (使用者插話)
else if progressSignalsThisTurn === 0 → handleSpinGuard (空轉保護)
else if allTasksDone && cleanEndPrompts < 2 → handleCleanEnd (乾淨結束)
else → queueContinuation (正常延續)
```

### 空轉偵測（Spin Guard）
- `progressSignalsThisTurn` 計數器：agent 每回合必須透過 `until_done_progress` 工具宣告進展（"what just shipped this turn"），否則計數為零
- 連續零進展觸發 spin guard — agent 在空轉（重複讀寫、寫日記但不推進）
- **設計洞察**：不依賴外部指標（如檔案修改時間），而是要求 agent 自我宣告進度 — 簡單且與目標追蹤緊密耦合

### 有界預算
- `maxTurns` 設於 contract，`HARD_BUDGET_CEILING` 防止過大值
- 預算耗盡不是 crash，是明確的狀態轉換（budget_exhausted），使用者可見

### 乾淨結束保護（Clean End）
- 所有任務完成後不立即標記 done，要求 `cleanEndPrompts < 2` — agent 必須在最後一輪確認「真的沒東西可做了」，防 premature completion
- 配合 verifiability block 的 "cleanup before completing" 條文

## 對應本專案的差距與改善空間

### 直接可用（高適用性）
1. **compact-continuation-bridge 的空轉風險**：我們的 compact-continuation-bridge 在 session compaction 後重新注入指導繼續工作，但無預算限制、無空轉偵測、無使用者插話暫停。若 agent 進入無限重構循環，harness 無法保護。應至少引入 turn budget 概念與明確的停止條件。
2. **進展宣告模式**：pi-until-done 要求 agent 每輪宣告 `until_done_progress` — harness 層可透過 skill 文字指導要求類似行為（如 planning-with-files skill 要求每輪更新 progress.md），但偵測需 bridge hook 支援。

### 概念借鑑
- **agent_settled vs agent_end**：pi-until-done README 明確寫 "agent_settled owns automatic continuation. agent_end is not used to queue work." — `agent_end` 在 session 真正結束（含使用者離開）時觸發，不適合自動延續。我們的 compact-continuation-bridge 用 `session_compact` hook，需確認 hook 選擇是否正確。
- **使用者插話優先**：`userMessagedThisTurn` 檢查確保使用者訊息不被自動延續覆蓋 — 自治系統必須尊重人類中斷。

## pi-until-done 的實作細節
- `progressSignalsThisTurn` / `codeEditsThisTurn` 在 `agent_start` hook 重置為零，回合邊界清晰
- spin guard 處理包含通知使用者與暫停目標（非靜默繼續）
- `userMessagedThisTurn` 由 input hook 在收到使用者訊息時設為 true
