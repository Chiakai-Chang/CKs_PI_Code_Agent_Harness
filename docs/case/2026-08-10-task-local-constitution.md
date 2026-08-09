# 每個任務的小憲法 —— 協定裡有,而我們從來沒載入過

**日期:2026-08-10**
**起因:** 擁有者指出 C.A.S.E. 的設計本來就是「拆成小任務、每次領一個、讀專屬 context」,
並問這樣是不是比在中途重述目標更容易對齊。

**答案:是,而且協定裡的東西已經齊了,只差沒有人載入。**

---

## 1. `role.md` 就是小憲法,每個任務都有一份

任務包的實際內容(取自 `external/Local-Agent-Workspace` 的範例任務):

```
Task_002_AnalyzeRepos/
  role.md      "You are a Principal Security Architect and AI Agent Framework
                Researcher. Your role is to analyze foreign repositories..."
  recipe.md    ## Objective / ## Input Sources / ## Output Specification
               ## Local Definition of Done (DoD)  ← 逐條 checkbox
  planning.md  output.md  status.txt
```

**全 repo 搜尋 `role.md` 的結果,只有兩處,兩處都不是載入:**

* `phase-gate.ts:214` —— 拒絕訊息裡**建議**模型自己去讀
* `pi-skills/commands/case.md` —— 一張說明用的表格

而本 repo 整週反覆量到的結論是:**建議不會被照做,只有拒絕與注入會**
(`when-an-instruction-is-ignored-change-its-shape`:重塑成表格欄位 3/3 被跳過,
只有 tool_call 層的拒絕讓 URL 從 0 變成 10)。

## 2. 為什麼「每個 task 像 local AGENTS.md 一樣生效」現在不會發生

推進器換下一個任務時用的是:

```ts
pi.sendMessage({ customType: "case-advance", ... },
               { deliverAs: "followUp", triggerTurn: true });
```

那是 **custom message,不是 user message**。`index.ts:216-219` 記著實測(session `019fcf32`):

> a custom message sat between an assistant turn that ended in text and a new
> assistant turn that made a real tool call, **with no user message between**

**所以換任務不會開新的 prompt cycle。** 而 `before_agent_start` 的宣告是
"Fired after user submits prompt" —— 沒有新的 user message,它就不會重跑。

結論:**憲法、Roadmap、小憲法,全都不會因為換了任務而重新出現。**
所有任務擠在同一個 prompt cycle 裡,目標只在最開頭講過一次。

這解釋了擁有者實測 session `019fe60f` 的觀感 ——
「有分階段、有用 MECE,但沒照 C.A.S.E. 走,也沒引導我驗收」。

## 3. 修法:接到已經存在、且已實測送得到的兩個通道

| 通道 | 觸發時機 | 送達證據 |
|---|---|---|
| `PhaseNotice.afterToolResult` | `status.txt` 變成 `IN_PROGRESS` —— **認領那一刻** | 已在真實 run 送達 |
| 推進器的 `step.message` | 換下一個任務時 | 乾淨重跑 11 次注入全送達 |

**認領任務時,注入該任務的 `role.md` + `recipe.md` 的 Objective 與 Local DoD。**

## 4. 為什麼這比 Task_019 的步數計數器好

| | Task_019 目標重述 | 任務小憲法注入 |
|---|---|---|
| 觸發 | 第 12 次工具結果(統計值,需校準) | **認領任務**(語意邊界,不需校準) |
| 內容 | 整段原始使用者請求 | **這個任務的角色與 Local DoD** |
| 驗證 | 需要造出會漂移的對照組 —— **三次失敗** | **二元**:session 紀錄裡有沒有出現 role.md 的內容 |
| 對齊判定 | 我得發明指標 | **協定已經定義**:該任務的 Local DoD 有沒有被滿足 |

第三、四列是重點。Task_019 的有效性卡了三輪,卡點是「造不出會失敗的對照組」
(見 `docs/measurements/2026-08-09-task019-preregistration.md`)。
**這個機制不需要那種對照組**,因為它要證明的事情本身是二元的。

## 5. 這不解決什麼

**單一任務內部跑 40 步,仍然會漂。** 擁有者自己也點出這一點。
所以 Task_019 沒有被取代,而是**換內容來源**:
從「重述原始使用者請求」改成「重述當前任務的 Local DoD」。

兩者是上下層,不是二選一:

* **任務邊界** → 注入小憲法(本次新做)
* **任務內部第 12 步** → 重述**該任務**的目標(既有機制,改內容源)

## 6. 關於 subagent 取代 compact

擁有者問:每次開 subagent 的話,是不是就不用做任務間的 compact?

**是,而且比 compact 更好。** Pi 的 subagent 就是 spawn 一個
`pi --print` 子行程(`deep-research-bridge/index.ts:85`,依 Pi 自己的
`examples/extensions/subagent` 範例)。子行程是**真正全新的 context**,
不是壓縮後的有損摘要;而且它有自己的 user prompt,
**所以 `before_agent_start` 會重跑** —— 那正是現在缺的那一件事。

**但有一個必須改的地方:** Pi 的範例(以及我們的 deep-research-bridge)用 `--no-session`,
而那**由設計上就不留稽核軌跡**。本 repo 的驗證紀律是「在 session JSONL 裡找到那段文字」,
`--no-session` 直接廢掉它。若走 subagent,必須改用 `--session-dir`
(`measure-advancer.py` 已經是這樣跑的)。

另有一條既有的疤:子代理曾在 repo 的 cwd 下帶著完整 write/edit/bash 執行,
無聲改動無關的原始碼(`subagents-need-a-write-boundary`)。
`yes-hooks-bridge` 的目錄圍堵在子行程裡也會載入,但**必須先驗證,不能假設**。

**建議順序不變:** 先做注入(小、便宜、驗證二元),subagent 與 compact 各自另案。
一次改一件事,否則分不清是誰的效果 —— 這正是我們今天才為此新增
`enableGoalRestate` 旗標的理由。

---

## 相關

* `docs/case/2026-08-09-anti-drift-gap-analysis.md` —— 為什麼中途沒有東西重述目標
* `docs/measurements/2026-08-09-task019-preregistration.md` —— 三次測不到的完整紀錄
* `01_Roadmap/roadmap.md` —— Phase 2c

---

# 實測結果(2026-08-10)

## 第一次:觸發 0 次,而原因不在新功能

Session `019fe880`,33 次工具呼叫,`status.txt` 全程 `PENDING`。
模型從第一次呼叫就跑到 harness 安裝目錄而不是自己的 cwd,認領從未成功,
所以掛在認領那一刻的注入自然一次也沒響。

查下去發現的是守衛互撞,已另立文件:
[四個守衛同時開口](2026-08-10-guards-collide.md)。

## 第二次:送達已證明

Session `019fe8a0`,提示裡把 cwd 講死之後,任務走到 `REVIEW`,`output.md` 788 bytes。

```
tool calls: 28   errored results: 9
TASK-CONSTITUTION BLOCKS DELIVERED: 1
```

注入區塊逐字出現在 `role: "toolResult"` 的紀錄裡:

```
[C.A.S.E.] 任務專屬憲法(不是指令輸出) —— 以下規則只適用於你剛認領的這個任務…
**你在這個任務裡的角色**
You are a Meticulous Inventory Auditor. 你只做清點與紀錄,不做任何修改,也不評論品質。
**這個任務的目標**
清點 src/ 底下所有模組並記錄數量。
**這個任務的驗收標準(Local DoD)**
- [ ] output.md 內含模組總數
- [ ] output.md 逐一列出模組檔名
```

而 `output.md` 裡出現了 `**稽核員角色**:Meticulous Inventory Auditor`、
一節 `## 完成標準對照` 逐條打勾,以及一節 `## 驗證指令`。

## 但這個 run **不能**歸因

工具呼叫序列顯示:

```
 8 read: 02_Task_Queue/Task_001_Inventory/recipe.md
 9 read: 02_Task_Queue/Task_001_Inventory/role.md
11 write: 02_Task_Queue/Task_001_Inventory/status.txt   ← 認領,注入在這裡
```

**模型在認領之前就自己讀了 role.md 與 recipe.md。**
所以交付物裡的角色與 DoD 對照,無法斷定來自注入。

**而且這個混淆是我們自己造成的:** 階段閘的第二階逐字寫著
「先 `read` 那個任務的 recipe.md 與 role.md(讀取不受限)」——
守衛把模型推去讀,然後注入又送一份。

## 由此得到的設計結論

**注入的價值最高的時候,正是模型不會自己去讀的時候。**
在階段閘會響的專案裡,兩者重疊;在階段閘不響(例如任務已經是 IN_PROGRESS、
或推進器換下一個任務)的路徑上,注入是唯一的來源 —— 而那正是原本的缺口:
換任務不開新 prompt cycle,小憲法永遠不會重新出現。

**現況:送達已證明,行為影響未歸因(n=1,且有已知混淆)。**
下一次量測要把階段閘那一階的「去讀 role.md」拿掉當作對照,或直接量推進器換任務的路徑。

