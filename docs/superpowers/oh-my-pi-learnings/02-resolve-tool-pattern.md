# oh-my-pi 學習筆記：Resolve 工具模式（Preview/Apply Handshake）

> 來源：`reference/oh-my-pi/docs/tools/resolve.md`、`docs/resolve-tool-runtime.md`

## 核心機制

oh-my-pi 的 `resolve` 工具實現了 **預覽/套用握手** 模式：

1. 產生預覽的工具（如 `ast_edit`）呼叫 `queueResolveHandler()`，註冊帶有 `apply(reason)` / `reject(reason)` 回呼的待處理動作
2. 預覽期間，會話返回 `SoftToolRequirement` — 非強制性提醒，模型可選擇忽略
3. 若模型忽略一次，系統才強制 `tool_choice: resolve` 一個回合（非消費性的 peek）
4. `resolve action="apply"` 執行註冊的 apply 回呼；`discard` 執行 reject 回呼或返回預設訊息
5. apply 失敗時重新排隊同一待處理動作，讓模型可重試或放棄

關鍵設計：resolve 本身不維護堆疊，只調度當前待處理的 invoker（queue invoker → pending invoker → standing handler）。

## 對本專案的啟發

### 直接可用
- **Bridge 啟用確認**：當 bridge 需要使用者確認的動作（如首次下載 camofox 引擎 ~300MB），可採用此模式：bridge 產生預覽（說明將要做什麼、下載大小），透過 Pi 工具提醒模型呼叫 confirm/resolve，而非靜默執行。
- **計畫模式保護**：oh-my-pi 用 resolve 保護 `ast_edit` 的 AST 結構化重構。我們的 `planning-with-files` skill 可引入類似模式：複雜計畫產生後不立即執行，先預覽等待確認。

### 概念借鑑
- **SoftToolRequirement 哲學**：非強制性提醒 + 一次忽略後才強制，比直接強制工具選擇更尊重模型判斷力，也比完全無提醒更有效。
- **失敗重試保留**：apply 失敗重新排隊而非丟失待處理動作，避免「失敗後一切歸零」的糟糕體驗。

### 改善空間（oh-my-pi 自身）
- pending invoker 以 `pending-action:<sourceTool>:<seq>` 為唯一鍵，無獨立深度上限；理論上可無限堆疊。
- discard 在無 reject 回呼時返回成功，apply 在無待處理動作時丟擲錯誤 — 對稱性不一致。
