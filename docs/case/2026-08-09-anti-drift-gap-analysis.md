# 對照 C.A.S.E.:反漂移機制的三個缺口

**日期:2026-08-09**
**問題來源:** 擁有者問「本地模型跑到第 18 步,還記得原本要完成什麼嗎?」
**結論:對這個失效模式,我們目前沒有任何機制。**

---

## 0. 為什麼要寫這一份

這個問題以前問過,而我們每次都用「我們有守衛」回答了它。這次去查,發現那個回答
成立的前提是一句從來沒被驗證過的假設,而那句假設寫在 `CLAUDE.md` 裡,由我自己寫的。

擁有者的原話值得逐字留著,因為它精確描述了守衛管不到的東西:

> 真正難的不是其中任何一步。而是跑到第 18 步還記得:「我原本到底要完成什麼?」

**守衛回答的是「這一步准不准」。漂移問的是「我還在做對的事嗎」。這是兩個不同的問題。**

---

## 1. 決定性證據:一則使用者訊息,十六輪 assistant

擁有者實測的 session,重跑計數(2026-08-09,寫這份文件時實跑):

```
2026-08-09T10-26-48-770Z_019fe60f-9542-7e07-9ce4-2b9ddcac26bf.jsonl
  user=1 assistant=16
  seq=Uaaaaaaaaaaaaaaaa
```

**目標只被說了一次,在第 0 輪。** 那之後的 16 輪裡,沒有任何東西再提過它。

## 2. 根因:所有帶著目標的注入,都掛在同一個事件上

安裝版 `types.d.ts` 對 `before_agent_start` 的宣告,逐字:

> Fired after user submits prompt but before agent loop

**「after user submits prompt」—— 每則使用者訊息一次,不是每輪一次。**

而目前掛在這個事件上的 bridge 有九個:

```
async-exec-bridge      compact-continuation(間接)   case-bridge(×2:162, 274)
ecc-hooks-bridge       mece-autopilot-bridge         planning-with-files-bridge:228
skill-catalog-bridge   task-shape-bridge             taste-bridge
yes-hooks-bridge
```

其中 `case-bridge/index.ts:274` 注入憲法 + Roadmap,`planning-with-files-bridge/index.ts:228`
注入可驗證性區塊。**兩者都是每則使用者訊息一次。** 在上面那個 session 裡,
它們在第 16 輪時已經是 15 輪之前的事。

### 2a. 我們自己的文件把這件事寫反了

`CLAUDE.md` 直到今天為止寫著:

> Verifiability block (planning-with-files-bridge): **injected each agent turn** while a plan is active

**不是每輪。** 這個錯誤的方向剛好是最糟的一種:它讓我們以為自己已經有中途強化,
於是這個缺口從來沒有被當成缺口。已於本次修正,並在 `CLAUDE.md` 的 Pi Extension Facts
一節補上量到的事實。

**教訓(與 `probe-the-event-not-the-type` 是同一族,但更難堪):**
這次型別註解**有寫**,是我們沒讀。我們拿探針驗過每一個自己蓋的守衛的觸發時機,
卻沒驗過繼承來的注入 —— **自己蓋的東西會被懷疑,繼承來的不會。**

## 3. 中途真的會發言的通道,說的全是同一種話

| 事件 | 訂閱者 | 內容性質 |
|---|---|---|
| `tool_call` | 目錄圍堵、階段閘、引用閘、tool-first、重複查詢 | 「不可以做這個」 |
| `tool_result` | 階段轉換通知、action log | 一次性通知 |
| `turn_end` | queue advancer(旗標預設關)、壓縮回音守衛 | 下一步(且只在模型停下講話時) |

**全部是「這一步對不對」,沒有一個是「你原本要做什麼」。**

這正是整週中心結論的另一面:擋阻只會說不。要對抗漂移,需要一個**會重述目標**的東西,
而我們一個都沒有。

## 4. 三個缺口(依失效模式的貴重程度排序)

### 缺口一:`[H]` Handoff Capsule 完全沒有實作 —— 最貴

協定 §16 與規劃範本的 `[H] Compaction & Handoff Capsule` 要求在 `planning.md` 維護:

- `session_summary` —— 到目前為止的進度與已做的決策
- `active_pivot_point` —— 現在正在動哪個檔案 / 函式
- `pending_blockers` —— 卡住的東西

驗證(2026-08-09 實跑):

```
grep -rn "handoff|active_pivot|session_summary|pending_blockers" pi-extensions/ --include=*.ts
```

只命中兩處**無關**的註解與工具說明字串(`queue-advancer.ts:62` 的英文 "handoff step"、
`stealth-web-bridge` 的 "VNC handoff")。**沒有任何東西寫它、讀它,或要求模型寫它。**

這一項的諷刺之處:我們有 `compact-continuation-bridge`,專門處理壓縮後的接續,
**而協定為同一個問題設計的資料結構,我們沒有接上去。**

### 缺口二:目標從不重述

憲法 / Roadmap 只在第 0 輪出現一次;`global_dod.md` 更徹底 ——

```
grep -rn "global_dod" pi-extensions/ --include=*.ts   →  (no output)
```

**沒有任何 bridge 提過它。** 這與 2026-08-08 那次的發現一致:`global_dod.md` 當時是一份
沒人讀過的未填範本。內容補好了,注入還是零。

### 缺口三:`[T]` 反重複沒有實作

協定要求動工前讀 `learnings.md`,避免重犯已知錯誤。`pi-extensions/` 裡對 learnings 的
命中全部來自 `ecc-hooks-bridge` 的**偵測與寫入**(hello-reflect),**沒有任何讀回注入**。
寫得進去、讀不回來。

## 5. 完整對照表

| 協定 | 用途 | 狀態 |
|---|---|---|
| §1 雙軌驗證 | 防自我核可 | ✅ 守衛 + Path A |
| §4 狀態機 | 防跳步 | ✅ 轉換守衛 + 狀態值合法性 |
| §6 Worker 協定 | 逐步執行 | ✅ 階段閘 + advancer(旗標關) |
| §7 Checker / Path A | 人類極簡驗收 | ✅ Task_018 |
| §13a 強制復盤 | 完成前必復盤 | ✅ 守衛擋 DONE |
| **§16 `[H]` Handoff Capsule** | **防第 18 步忘記目標** | ❌ **未實作** |
| **`[T]` 反重複(learnings.md)** | 防重犯 | ❌ **未注入** |
| `[R]` Plan Self-Review | 動工前自審 | ⚠️ 只檢查標題存在,不檢查內容 |
| `[V]` 驗收準則 | 交付前驗證 | ⚠️ 只檢查 `output.md` ≥200 字 |
| §17 跨模型 Checker | 驗證誠實性 | ⚠️ 單模型;Path A 是協定認可的等價路徑 |
| Global DoD | 全域對齊 | ❌ 從未注入 |

`[R]` 與 `[V]` 標 ⚠️ 而非 ✅,理由相同:**兩者檢查的都是形狀,不是內容。**
一個標題存在、一份 200 字的 `output.md`,都可以在完全漂移的情況下滿足。
這正是 `count-the-checks-that-can-actually-fail` 記過的那一類。

## 6. 修的順序(尚未動工,等核可)

**先做缺口二 —— 最便宜、最直接。** 目標重述要掛在**中途會發言且已被實測證明送得到**
的通道上:`tool_result` 回傳 `{content:[...existing, block]}`。形式例如每 N 次工具呼叫後
附一行「目前任務目標:…;你在第 X 步」。

**再做缺口一。** Handoff Capsule 需要模型配合寫,而整週的結論是
**建議不會被照做,只有拒絕會**(`when-an-instruction-is-ignored-change-its-shape`)。
所以它大概要做成「沒有 `[H]` 區塊就擋下交付物寫入」,與 `planning.md` 的 Self-Review
檢查同型。

**缺口三最後**,因為 `learnings.md` 目前在多數專案是空的,先做等於注入空字串。

### 動工前必須先想清楚的一件事

`gates-create-their-own-failure-mode` 說過:門檻定義了規避的形狀。
**目標重述如果每輪都注入,它會變成模型學會略過的樣板文字。** 所以第一件事不是寫注入,
而是**先想好「怎麼量它有沒有用」** —— 而且要在動工前寫下來,不是事後找數字。
候選指標:同一 session 內偏離原始請求的輪次比例;是否還能在最後一輪講出原始目標。

## 7. 這次的方法論收穫

1. **繼承來的機制沒有被懷疑過。** 我們對自己蓋的每一個守衛都做了觸發探針,
   而九個 `before_agent_start` 注入從來沒有人問過「它多久跑一次」。
2. **文件寫錯的方向決定它有多危險。** 「我們有中途強化」比「我們沒有文件」更糟,
   因為前者會關閉調查。
3. **整週在管入口,而問題在續航。** 所有機制回答「這一步准不准」,
   沒有一個回答「你還在做對的事嗎」。這不是實作缺陷,是**問題沒被提出來過**。

---

## 相關

- `CLAUDE.md` — 已修正錯誤描述,已補 `before_agent_start` 觸發頻率事實
- `01_Roadmap/roadmap.md` — Phase 2c 三個缺口
- `docs/case/task-011-blocked-claim-channel.md` — 「證明文字送達模型」的同族教訓
- `docs/case/task-018-path-a-human-review.md` — 上一次「協定裡有,我們沒讀」
