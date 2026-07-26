# 收穫四：Compaction 生存套件與工具註冊模式

> 來源：pi-until-done 的 compaction-context.ts、session_compact hook、工具註冊架構。
> 對應本專案：compact-continuation-bridge 正是為此問題而生；stealth-web-bridge 的工具註冊可對照。

## pi-until-done 的設計

### Compaction 生存套件（Compaction Context）
**核心洞察**：lossy compaction 會丟棄大部分對話內容，必須在壓縮前注入「生存套件」標記哪些內容不可丟棄。

```ts
export const compactionAnnotation = (s: GoalState): string => {
    const lines = [
        "",
        "[/until-done · compaction context — preserve everything below verbatim]",
        headline(s),            // goal + turn budget + phase
        verifyLine(s),          // verify command
        surfacesLine(s),        // 可達證據表面
        currentTaskLine(s),     // 當前任務
        ...recentEvidence(s),   // 最近 6 筆證據（verbatim）
        ...recentLearnings(s),  // 最近 8 筆學習（verbatim）
    ];
    return lines.join("\n");
};
```

- hook 選擇：`session_compact` 排程隱藏 CustomMessageEntry 在下一輪重新錨定；**不使用 `session_before_compact`**（README 註明 "ineffective prompt mutation" — 壓縮前修改 prompt 無效）
- 生存套件只保留「壓縮後最需要的信號」：goal、verify command、當前任務、最近證據/學習 — 不是完整狀態副本
- 標記 `preserve everything below verbatim` 指導 compaction 模型保留此區塊

### 工具註冊模式
```ts
pi.registerTool({
    name: "until_done_complete",
    label: TOOL_LABELS.complete,
    description: TOOL_DESCRIPTIONS.complete,
    parameters: CompleteParams,       // TypeBox schema
    async execute(_id, params, _signal, _onUpdate, ctx) {
        return executeComplete(pi, store, params, ctx);
    },
});
```

- 參數 schema 用 TypeBox（Pi 工具標準），schema 與執行邏輯分離
- 工具描述/標籤/結果文字集中在 strings/ 模組，非硬編碼在註冊處
- 執行函數接受 `(pi, store, params, ctx)` — pi/store 透過 closure 注入，params/ctx 來自 Pi 呼叫
- 結果用統一 `ok()` / `failed()` / `refused()` 建構，含 status metadata

### 拒絕模式（Refusals）
- 狀態檢查前置：`if (s.status !== "active") return failed(REFUSAL.noActiveBlock(s.status))`
- 拒絕訊息包含當前狀態（`status=${status}`）— 除錯友好
- 工具不執行時回 `failed()`，非 `refused()` — Pi 工具結果語義的有意選擇

## 對應本專案的差距與改善空間

### 直接可用（高適用性）
1. **compact-continuation-bridge 的 compaction 策略**：我們的 bridge 在 session_compact 後重新注入指導，但無 pi-until-done 式的「生存套件」設計 — 沒有明確標記哪些內容不可丟棄、沒有最近證據/學習的精簡保留。應引入 verbatim preservation 區塊概念，確保壓縮後關鍵指導（實測有證據原則、當前任務狀態）不被丟失。
2. **hook 選擇文檔**：pi-until-done README 明確寫出為何不用 `session_before_compact` — 我們的 compact-continuation-bridge 應在 RATIONALE.md 中文件化 hook 選擇理由。

### 可對照檢查
- stealth-web-bridge 的工具註冊模式與 pi-until-done 對比：參數 schema、結果建構、錯誤處理是否一致？（需實查）

## pi-until-done 的實作細節
- compaction annotation 在 `session_compact` hook 中作為隱藏 CustomMessageEntry 排程，非直接注入 prompt
- RECENT_EVIDENCE_KEEP=6、RECENT_LEARNINGS_KEEP=8 — 精調過的保留數量，平衡信號密度與 token 成本
- verify command 路由：`routeThroughMise(params.verifyCommand)` 自動包層 `mise exec --`，但已以 `mise run/exec` 開頭的命令保留原樣 — 細節防禦
