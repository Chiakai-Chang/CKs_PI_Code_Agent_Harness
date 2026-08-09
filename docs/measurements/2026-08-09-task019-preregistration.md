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

---

# 結果 —— 第一次真實 run(2026-08-09,寫在跑完之後)

Session:`019fe72a-0db2-786a-8126-2118b89d5503`,乾淨的暫存工作目錄,
20 個檔案,4-deliverable 提示(事先確認 `classifyRequest` 判為 multi-step)。

## 送達:已證明

```
user=1 assistant=8 toolCalls=20
restatement messages found: 1
seq=Uaaaa!aaaa
```

命中位置是 **`role: "toolResult"` 的紀錄** —— 也就是真的接在工具結果上送給模型,
不是只印在 TUI。內容逐條核對:

```
  PASS  header present            [task-shape] 目標重述
  PASS  quotes the request        含 "逐一讀取" 與 "summary.md"
  PASS  states the count          "呼叫了 12 次工具"(措辭已於本次修正,見下)
  PASS  asks the question         "仍然在回答"
  PASS  not truncated             短提示未標截斷
```

**觸發次數 1 次是正確的,不是少響。** 門檻 12、命中後歸零,第二次要再 12 次(共 24),
這個 run 只有 20 次。

**位置 14 是批次假象,不是計數錯誤。** assistant 每輪批次發出工具呼叫,
本 run 是 2/4/4/4/4/1/1;第 12 個結果落在第四批內(2+4+4+4=14)。
20 個 toolResult 全部 `isError=false`,所以錯誤過濾在這個 run 上沒有被測到。

## 反向指標

| 指標 | 結果 |
|---|---|
| 每 cycle 工具呼叫總數 | 20。沒有重工跡象(序列 `bash bash read×16 write read`) |
| 交付物長度 | `summary.md` 1915 bytes,有產出 |
| 重述後工具序列是否改變 | **沒有改變** |
| 使用者可見雜訊 | 無。不經 `ctx.ui.notify` |

## 這個 run **沒有**證明的事(重要)

**模型從頭到尾沒有漂移。** 它讀完全部檔案、寫出表格、產出交付物 —— 完全在做對的事。

所以第三項反向指標「序列沒有改變」在這裡**不能**判讀為「已成為樣板文字」:
一個本來就在正軌上的 run,重述沒有東西可以修正,不變才是對的。

**主要指標(末段對齊率)完全沒有被測到。** 這個 run 不含漂移案例。
依判定規則,現況是:

* **送達 = 已證明**(這是原本最可能失敗的一環,`notify-is-not-a-channel-to-the-model` 的疤)
* **有效 = 未證明,且本 run 無法證明**
* 不套用「撤回」——「觸發 0 次」沒有發生。
* 不套用「保留」—— 保留需要主要指標有改善,而它沒有被測到。

**下一步不是再跑一次同樣的 run。** 需要的是一個**會漂移**的情境:
長 cycle、目標與中途誘因衝突。這件事現在就承認做不到單純靠重跑,
而不是等到報數字時才說。

## 一項回頭修正 prior-art 分歧的證據

`oh-my-pi-can1357` 只數變更型工具;我們數全部。這個 run 的序列是
`bash bash read×16 write read` —— **依它的規則只會累積 3 次**(2 bash + 1 write),
永遠不會觸發。依我們的規則觸發 1 次。

在這個工作量下,我們的選擇是對的;但它同時說明兩者差距有多大,
而 32.4% 的校準只支持我們這一邊。**這條分歧仍是最可能挑錯的參數。**

## 讀 log 才發現的一個不準確(已修)

重述原文寫「你到目前為止已經呼叫了 **12** 次工具」。
但觸發那一刻,模型其實已經發出 **14** 次呼叫 —— 我們數的是**回來的結果數**,
它看到的是**發出的呼叫數**,而批次(2/4/4/4/4/1/1)讓兩者分岔。

**這個機制存在的理由,就是告訴模型一件它無法自我觀察的事;
那這件事就必須是對的。** 措辭改為「已經有 N 次工具結果回來(批次發出的呼叫數可能更多)」,
並補 `test_counts_results_not_calls` 釘住。

這一項是**讀 session log 才看得到的**:單元測試永遠不會發現,
因為它不知道真實 run 會批次發送。

## 另外兩個從 log 讀出來的觀察

* **兩個乘客共用通道,都送到了。** routing note 1 筆、目標重述 1 筆,互不吞噬。
  合併回傳(而非先到先返回)是必要的,不是保險。
* **注入 190 字元,接在 47 字元的工具輸出後面。** 在小輸出上,我們的文字是工具本身的四倍;
  在大輸出上會被埋掉。**注入的相對可見度隨工具輸出大小反向變動**,而這件事沒有被設計過,
  也還沒有被量過。

