# 收穫三：Session 原生狀態管理與 Hook 組合紀律

> 來源：pi-until-done 的 store.ts（typed custom entries + reducer replay）、hooks/ 模組化架構。
> 對應本專案：skill-namespace-guard 在 resources_discover 時寫入報告但無持久狀態；各 bridge hook 使用無統一紀律文件。

## pi-until-done 的設計

### Session 原生狀態（Store）
**權威狀態在 Pi session branch 上，不在檔案系統 side database。**

```ts
// 持久化：typed custom entry 寫入 session branch
pi.appendEntry<StateEvent>(STATE_CUSTOM_TYPE, event);

// 重建：session_start 時從 session entries replay 事件
reconstructFromSession(pi, store, ctx);
```

- 每個狀態變更（set/progress/verdict/block/complete）都 append 一個 typed event entry，含 schemaVersion、kind、patch、note
- `reconstructFromSession` 掃描 session branch 的 custom entries，用 reducer 重放重建 state — **branch 切換時自動重建**（Pi 的 `/tree` 導航到新分支，狀態跟隨）
- `.until-done/tasks.yaml` 和 `.until-done/distilled.md` 是 inspectable exports，**不是 side database**
- 舊版狀態遷移：append migration event，**永不重寫歷史**；無效遺留狀態安全暫停

### Hook 組合紀律（README Runtime Contract）
```
• before_agent_start appends the active North Star to event.systemPrompt;
  it never replaces another extension's prompt.
• agent_settled owns automatic continuation. agent_end is not used to queue work.
• session_compact schedules a hidden CustomMessageEntry re-anchor on next turn.
• session_before_compact is intentionally NOT used (ineffective prompt mutation).
• Uninvolved hook handlers return undefined.
```

### 模組化 Hook 架構
- `hooks/agent.ts`：只處理 agent lifecycle（start/settled），組合子 handler
- `hooks/before-agent-start.ts`：只處理 system prompt 附加，buildReminder 函數純計算
- `hooks/session.ts`：session lifecycle（start/switch/fork/export），含 startup flag 處理
- `hooks/compaction-context.ts`：compaction 生存套件生成（見收穫四）
- `hooks/tools.ts`：工具註冊時的副作用（如 registerTool 後的狀態檢查）
- 每個 hook handler 獨立 concern，store 透過 closure 注入

## 對應本專案的差距與改善空間

### 直接可用（高適用性）
1. **Hook 紀律文件化**：我們的 bridge 使用多個 Pi hooks（resources_discover、session_compact、tool_call 等）但無統一紀律文件。應在 pi-rules/ 或 extensions/ 層級文件化 hook 使用原則，至少涵蓋：system prompt 附加永不替換、hook 選擇理由（為何用 A 不用 B）、不涉入的 handler 回 undefined。
2. **skill-namespace-guard 報告的持久化**：目前寫入 pi-config/skill-conflict-report.json（檔案系統），但 Pi session branch 切換或新 session 時衝突狀態不跟隨。若衝突檢測是 session 相關決策，應考慮 session-native 記錄。

### 概念借鑑
- **Reducer replay 模式**：pi-until-done 把 oh-my-pi 內部用的 session entry 模式應用到 extension 狀態管理 — harness 層若有跨回合狀態需求（如 compact-continuation 的延續上下文），可參考此模式而非純靠 skill 文字注入。
- **永不重寫歷史**：遷移 append migration event 不重寫舊 entries — 此原則應適用於 harness 任何版本化狀態（bridge manifest、external manifest）。

## pi-until-done 的實作細節
- `store` 含 runtime-only 欄位（progressSignalsThisTurn、lastAssistantText）與 persisted state 分離，persist() 只寫 state patch
- session_switch hook 用 `ctx.ui.confirm()` 互動確認離開 active goal，回 `{cancel:true}` 取消切換
- fork hook 提供選擇：carry goal 到新分支 vs leave behind — 狀態隨分支的明確語義
