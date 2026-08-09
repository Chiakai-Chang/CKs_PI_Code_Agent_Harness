# Task_019 目標重述 —— 預先登記(寫在任何程式碼之前)

**日期:2026-08-09。寫這份文件時,`goal-restate.ts` 還不存在。**

這份文件先寫,是因為 `gates-create-their-own-failure-mode` 與
`a-guard-that-never-fired-is-unvalidated` 兩條疤都指向同一件事:
**事後找數字的人一定找得到數字。** 觸發條件、主要指標、反向指標與判定規則,
全部在動工前寫死。

---

## 0. Prior Art(先查既有)

| 來源 | 位置 | 決定 |
|---|---|---|
| `research/oh-my-pi-can1357` mid-run todo nudge | `src/session/todo-tracker.ts:287` `takeMidRunNudge()`、`src/prompts/system/mid-run-todo-nudge.md` | **移植設計,不移植實作** |
| 我們自己的 `case-bridge/phase-notice.ts` | `afterToolResult()` | **沿用注入樣式** |
| 我們自己的 `task-shape-bridge` | `index.ts` | **當宿主**,不新建 bridge |

**這是我們 clone 了卻標「未審視」的來源。** 它已經實作了 Task_019 要的能力,
而 register 上是 17 個未審視之一 —— 又一次「cloned ≠ reviewed」。

從它移植的四個設計決定,逐條:

1. **以「動作數」計數,不以「輪數」計數。** 它數的是 `mutationsSinceLastTouch`,
   在模型碰了狀態工具時歸零(`todo-tracker.ts:104-111`)。也就是
   **「做了很多事卻沒回頭看計畫」才提醒**,而不是每 N 輪都念一次。
2. **硬上限。** `MID_RUN_NUDGE_MAX_PER_CYCLE = 2`。稀有是設計的一部分。
3. **每個 prompt cycle 歸零**(`resetCycle()`)。
4. **在注入當下才求值**,所以剛更新過狀態的那一輪會抑制提醒
   (`agent-session.ts:1206-1208` 的註解逐字寫了這個理由)。

**不移植的部分:** 它是 pi 核心的 fork,能 `appendMessage`。我們只有 extension 事件,
所以載具必須是 `tool_result` 回傳 `{content:[...existing, block]}` ——
本 repo 唯一實測證明送得到模型的中途通道。

## 1. 假設

長 cycle(一則使用者訊息、數十次工具呼叫)裡,原始請求只在第 0 輪出現一次。
在中途把**使用者的原話**重新放回模型眼前,會減少末段偏離原始請求的情形。

## 2. 觸發條件(先寫死,再量)

一個 run 必須**做到什麼**才會讓它響:

* 同一個 prompt cycle 內,累積 **≥ 12 次成功的實質工具呼叫**(mutating 或 broad),
* 且該 cycle 被 `classifyRequest` 判為 **multi-step**,
* 且本 cycle 已發出的重述 **< 2 次**,
* 且該次 `tool_result` **非錯誤**。

計數在每次注入後歸零,在每個 `before_agent_start` 歸零。

**門檻 12 的依據(2026-08-09 實跑,非估計):**

```
user-prompt cycles across real sessions: 219
  tool calls per cycle: median=2 p75=18 p90=38 p95=52 max=811
  cycles with >= 12 tool calls:   71  (32.4%)
```

分佈是雙峰的:median 2,p90 38。門檻 12 讓它在短 cycle 完全安靜,
在約三分之一的真實 cycle 響一次。與 prior art 的 12 相同純屬巧合,但兩邊都不是憑感覺挑的。

## 3. 主要指標

**末段對齊率:** 在工具呼叫 ≥ 12 的 cycle 裡,最後一則 assistant 文字是否仍在回答原始請求。

判定必須人工或跨模型做 —— 我們沒有可信的自動 judge,而
`07-optimization-plan.md` 的「judge 是 extension 層的事」這個排除已被記錄過一次誤反轉。
**因此本項的樣本會很小,而這一點現在就承認,不等到報數字時才說。**

## 4. 反向指標(門檻定義規避的形狀)

`gates-create-their-own-failure-mode`:引用閘把 URL 從 0 拉到 10,同一個 run 也把
編造的 URL 從 0 拉到 4。所以**必須同時記下這次沒有瞄準的數字**:

| 反向指標 | 為什麼要看 | 惡化的意義 |
|---|---|---|
| 每 cycle 工具呼叫總數 | 重述可能讓模型重啟已完成的工作 | 變多 = 製造了重工 |
| 交付物長度 | 重述可能排擠實質內容 | 變短 = 用篇幅換對齊 |
| 重述後是否立刻改變工具序列 | 沒有任何行為改變 = 樣板文字 | 完全無變化 = 已被學會略過 |
| 使用者可見的雜訊 | 這個注入對使用者不可見,但 `ctx.ui.notify` 會 | 過吵 = 會被關掉 |

## 5. 判定規則(先寫,不事後改)

* **保留** —— 主要指標在 ≥ 12 工具呼叫的 cycle 上有改善,且四項反向指標皆未惡化。
* **改形** —— 觸發了但行為無變化(第 3 項反向指標)。這代表載具或措辭錯,不是概念錯;
  依 `when-an-instruction-is-ignored-change-its-shape`,下一步是改形狀而非加字。
* **撤回** —— 任一反向指標惡化,或它在真實 session 從未觸發。

**「觸發 0 次」算失敗,不算沒事。** 這是 `a-guard-that-never-fired-is-unvalidated` 的規定。

## 6. 現在就承認的限制

* Global DoD 第 6 條(噪音底線)仍是 ❌。本機模型的 run 間變異**沒有量過**,
  所以任何「改善了」的宣稱都會受制於 n。這份預先登記**不會**因為數字好看就繞過這一條。
* 主要指標需要判讀,沒有自動化。小樣本是已知的,不是事後才發現的。
* 本項只處理缺口二(目標從不重述)。缺口一(`[H]` Handoff Capsule)與
  缺口三(learnings 注入)不在本次範圍。
