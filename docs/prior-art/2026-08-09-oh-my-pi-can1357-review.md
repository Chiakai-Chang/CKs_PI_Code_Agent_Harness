# oh-my-pi-can1357 審視 —— 它已經解決了我們今天才發現的問題

**日期:2026-08-09**
**範圍:刻意窄。** 只讀了與 Task_019(中途目標重述)直接相關的部分,不是整棵樹。
依審視程序第 (2) 條:讀離當前問題最近的兩三件事。

---

## 0. Provenance 先於內容

* 這不是提案或策略文件,是**出貨的實作**:`packages/coding-agent/src/session/todo-tracker.ts`
  與 `src/prompts/system/mid-run-todo-nudge.md`。
* 它有**回歸測試**,且測試 docstring 逐字寫出它防的 issue 編號與五條契約
  (`test/agent-session-todo-mid-run-nudge.test.ts`)。
* 它是 **pi 核心的 fork**(`@oh-my-pi/pi-coding-agent`),不是 extension。
  這一點決定了什麼可移植、什麼不可移植。

## 1. 對我們的意義

2026-08-09 我們才發現本 harness 沒有任何東西在中途重述目標
(見 [反漂移缺口分析](../case/2026-08-09-anti-drift-gap-analysis.md))。
**這個 clone 已經實作了那個能力,而且我們 clone 它之後從沒讀過。**

它的名字叫 mid-run todo reconciliation nudge,不叫「目標重述」——
這正是為什麼關鍵字搜尋 register 找不到它,而必須真的去讀。

## 2. 移植了什麼(設計,不是程式碼)

| 決定 | 它的位置 | 我們的 `goal-restate.ts` |
|---|---|---|
| 數動作而非數輪次 | `todo-tracker.ts:104-111` | ✅ 同樣 |
| 每 cycle 硬上限 | `MID_RUN_NUDGE_MAX_PER_CYCLE = 2` | ✅ `MAX_RESTATEMENTS = 2` |
| 每 prompt cycle 歸零 | `resetCycle()` | ✅ `begin()` |
| 注入當下才求值 | `agent-session.ts:1206-1208` 的註解 | ✅ 在 `tool_result` handler 內求值 |
| 對使用者隱藏 | `display: false` | ✅ 只進 tool result content |

**沒有移植:載具。** 它 fork 了核心,可以 `appendMessage`。
我們只有 extension 事件,唯一實測送得到模型的中途通道是
`tool_result` 回傳 `{content:[...existing, block]}`。

## 3. 刻意分歧的一項 —— 而且它可能是錯的

**它只數「成功的變更型」工具結果**(bash/eval/edit/write/ast_edit),
`grep`/`read`/`glob`/`lsp` **不算**,錯誤也不算(測試契約第 1 條)。

**我們數所有成功的工具呼叫。**

理由:門檻 12 是對本機 219 個真實 cycle 的**全部工具呼叫**分佈校準出來的
(median 2、p75 18、p90 38、p95 52、max 811;≥12 的佔 32.4%)。
只數子集會讓那個 32.4% 立刻失效,而校準是這個門檻唯一不憑感覺的依據。

**但兩個 12 意義完全不同。** 它的 12 次變更是高得多的門檻;我們的 12 次任意呼叫
在探索密集的 run 上會早很多響。**這是本次最可能挑錯的參數**,
已寫進預先登記的判定規則:若反向指標「重述後工具序列無變化」成立,先改形狀不加字。

## 4. 這次審視對我們自己的發現

**又一次「cited ≠ reviewed」。** 我在 `goal-restate.ts` 的檔頭與預先登記文件裡引用了
這個來源,而 register 上它是「未審視」。**`scripts/check-prior-art.py` 當場擋下**:

```
[FAIL] oh-my-pi-can1357 is cited as a reason in
docs/measurements/2026-08-09-task019-preregistration.md,
pi-extensions/task-shape-bridge/goal-restate.ts
but the register still says 未審視. Citing it is using it — review it, or stop leaning on it.
```

這個檢查是 2026-08-09 稍早才加的,**第一次真正觸發就是抓到我自己**。
上一次同型問題是靠人想起來的。

## 5. 未移植 / 拒絕,以及讓我們回頭考慮的觸發條件

| 項目 | 決定 | 觸發條件 |
|---|---|---|
| `todo` 工具本身(phased init、任務標籤) | **不採用** | 我們的計畫層是 `planning.md` 與 C.A.S.E. 任務包;再加一個 todo 工具會是第三套狀態 |
| `eager-todo` 強制先建 todo(`forced` 分支) | **暫不採用** | 與 `task-shape-bridge` 的 routing note 職責重疊;若 routing note 被量到無效,這是下一個形狀 |
| stop-time reminder ladder(停下時追進度,`reminderCount/remindersMax`) | **待評估** | 這是「模型停下但工作未完」的機制,與我們的 queue advancer 同位;advancer 目前預設關,兩者要一起決定 |
| `buildPostCompactionEagerNudges()` | **待評估,且與缺口一相關** | 壓縮後重新注入 —— 這正是 `[H]` Handoff Capsule 要解的問題,做 Task_020 時必須先回來讀這一段 |

## 6. 磁碟

3.3 GB,是四個大 clone 之一。**本次審視之後它不再是「留著沒讀」** ——
第 5 節的 stop-time ladder 與 post-compaction nudges 是兩個具名的回訪點。
