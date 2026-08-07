# 重新參考 pi-until-done:續跑迴圈的實作層對照

> **這份不是摘要,是對照。** 上一份筆記
> (`docs/superpowers/pi-until-done-learnings/02-*.md`)寫得沒錯,而我們沒有照著做,
> 所以這次逐行讀 `reference/pi-until-done/extensions/lib/`,把我們的推進器與它並排。
>
> 讀的版本:`pi-until-done` 鎖 Pi `0.81.1`,本機 Pi 是 `0.83.0` ——
> **不能直接安裝,只能移植機制**。這一條先確認,免得移植到一半才發現。

## 一、事件位置:`agent_settled`,不是 `turn_end`

`extensions/lib/hooks/agent.ts:62` 只掛一個續跑事件:

```ts
pi.on("agent_settled", async (_event, ctx) => { ... handleEndTransitions(...) })
```

`turn_end`(`hooks/turn.ts:35`)在它們手上**只用來記住最後一段助理文字**,不做決策。

我們的推進器掛在 `turn_end`,於是每一輪都說話。**這就是 Task_008 量到「正常進行中的步驟
被判成停滯」的直接成因** —— 不是門檻調太低,是位置選錯。

## 二、停滯的判準是「這一輪有沒有做事」,不是「注入了幾次」

`hooks/tools.ts:65` 在 **`tool_call`** 上為每個呼叫加權計分:

| 動作 | 分數 |
|---|---|
| `edit` / `write` | +3(另計 `codeEditsThisTurn`) |
| `bash` | +2 |
| `read` / `grep` / `find` / `ls` | +1 |
| 其他工具(非 `until_done_*`) | +2 |

`hooks/agent.ts` 的狀態機:

```
turnsUsed >= maxTurns          → handleBudgetExhausted  (暫停)
userMessagedThisTurn           → 不續跑,記 verdict     (使用者插話優先)
progressSignalsThisTurn === 0  → handleSpinGuard        (擋下,標記 blocked)
CI 失敗                        → 不續跑
allTasksDone && cleanEndPrompts < 2 → handleCleanEnd    (最多兩次收尾提示)
否則                            → queueContinuation
```

**我們的退場計數器數的是「我說了幾次」,它數的是「你做了什麼」。** 一個做了 20 次工具呼叫
卻還沒改完 status 的回合,在它那裡是健康的;在我們這裡第四輪就被宣告卡住。

## 三、額度用完是**暫停**,不是把任務標成失敗

`hooks/agent-end-helpers.ts:13` 的 `handleBudgetExhausted` 只做兩件事:
把 **loop 自己的** `status` 設成 `paused`、通知使用者。`handleSpinGuard` 同理,設 `blocked`。

**它從不去動被執行任務的狀態。** 我們的推進器擋不動時,要求模型把 `status.txt` 改成
`ESCALATED` —— 那是**協定的任務狀態**,代表「這件事卡住了,交還人類裁定」。

於是「自動化放棄了」被寫成了「任務失敗了」。Task_008 五次 run 有三次終態 ESCALATED,
其中至少兩次任務本身進行得好好的。**這是我們自己造出來的假失敗。**

## 四、續跑用 `sendUserMessage(..., { deliverAs: "followUp" })`

`agent-end-helpers.ts:93`。注意兩件事:

* 用的是 **`sendUserMessage`**,不是 `sendMessage` —— 續跑訊息以使用者訊息的身分進入,
  而不是自訂型別的系統訊息。
* **沒有 `triggerTurn`**。我們的推進器用 `sendMessage(..., {deliverAs:"followUp", triggerTurn:true})`。
  在 `agent_settled` 這個時點,followUp 本身就足以讓下一輪發生;
  `triggerTurn` 是我們掛在 `turn_end` 時為了硬推一輪而加的。**位置換了,這個參數也要重評。**

續跑訊息內容(`continuation.ts`)每次重述:目標、完成條件、驗證指令、目前階段、
以及一段固定的 TDD 與 verifiability 紀律 —— 並截斷到 4000 字元(`RESPONSE_SNIPPET_CHARS`)。

## 五、預算的形狀

`constants.ts`:`DEFAULT_MAX_TURNS = 20`,硬上限 `HARD_BUDGET_CEILING = 20000`,
超過 `500` 要使用者在對話框裡確認。註解寫得很清楚:**上限是粗糙的最後保險,
真正的守門是那些正交的閘**(spin guard、clean-end、CI 失敗、使用者插話、壓縮)。

我們只有一個 `MAX_ADVANCES_PER_STEP = 3`,同時扮演節流、停滯偵測與升級三種角色。

## 六、judge:被我們排除、又被我們用正規表達式重做一遍

`tools/judge.ts` + `judge-request.ts`:完成聲明送給**另一個模型**,只看
goal / doneCriteria / verifyCommand / 執行者引用的證據,**不看執行過程**,
回傳嚴格 JSON `{verdict: "done"|"continue", reason}`;解析失敗或模型不可用時
**fail open 但顯示警告**,沒有「靜默略過」的旁路。

`docs/superpowers/pi-until-done-learnings/07-optimization-plan.md` 當時把它列為
「不實作 —— 擴充層職責」。而 2026-08-06 我們花了兩個任務(Task_010、Task_011)
做 `blocked-claim`:用詞表與結構規則判斷「回覆是不是謊報完成」。

**那就是一個很弱的 judge。** 那條排除決定事實上已經被推翻,只是沒有人寫下來。

## 直接可移植的四項(給 Task_015 用)

| # | 移植什麼 | 取代我們的什麼 | 風險 |
|---|---|---|---|
| 1 | 續跑改掛 `agent_settled` | `turn_end` 每輪注入 | `agent_settled` 的實際觸發時機要先探針量過,不能只讀型別 |
| 2 | 加權 progress signal,`=== 0` 才算停滯 | 數注入次數 | 權重是它們的經驗值,我們要記錄自己的觀察 |
| 3 | 自動化放棄 = 暫停自己,**不動 `status.txt`** | 要求模型寫 ESCALATED | 需要一個 loop 自己的狀態存放處 |
| 4 | 終端步驟不計時 | 交還使用者的步驟被判卡住 | 協定要標明哪些是終端狀態(已列為 CASE 上游回饋) |

**不移植**:turn budget 的對話框確認(我們是 `--print` 為主的量測場景)、
YAML 狀態檔與 widget UI(TUI 專屬,對模型不可見)、`mise` 綁定的驗證指令路由。

## 一句話

**我們的推進器與它的差別不在功能多寡,在「誰的狀態」被改。**
它讓自動化在自己的狀態機裡失敗,任務狀態始終由協定與人決定;
我們讓自動化直接去寫協定狀態,於是自動化的每一次放棄都變成任務的失敗紀錄。
