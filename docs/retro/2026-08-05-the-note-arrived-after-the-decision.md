# 復盤：通知在決定之後才到（2026-08-05）

這份記的是一次**設計失敗**，以及失敗的原因為什麼比失敗本身更值得留下。

Harness 主人的問題很具體：請 Pi 做市場調查，它直接搜十幾次然後給結論，而 Superpowers、planning-with-files、MECE-Autopilot、C.A.S.E. 都裝著。

量化之後：

```
debug-methodology         2/3   67%
multi-step-methodology    0/3    0%
```

我建了 `task-shape-bridge`：偵測多步請求 → 在第一個廣域工具呼叫時投遞一份具體腳本。單元測試 24 個全綠、負向對照 3/3 不誤觸發、13 個 bridge 0 failures。

驗收量測：**0/3。一點都沒動。**

---

## 一、失敗的原因可以精確指出

實測 session log 顯示腳本**確實送達了**：

```
>>> toolResult #1 (web_search) 含 routine:
[task-shape] routing note (not command output):
This request looks like 3 separate deliverables. Before searching, take one of two paths: ...

total toolResults: 17 | routine delivered: True
tool calls: web_search × 4, web_open × 3, web_search ...
```

模型在 17 次工具呼叫裡完全無視它，全是搜尋與開網頁，沒有計畫、沒有讀任何 skill。

原因不是「文字沒用」，是**位置錯了**：

```ts
ToolCallEventResult { block?: boolean; reason?: string; }   // 沒有第三個欄位
```

`tool_call` 階段**無法注入文字，只能擋**。所以「在動作發生的那一刻建議」實際上是「在動作發生**之後**建議」——腳本出現在第一次搜尋的**結果**裡，模型已經投入、資料已經到手，繼續搜是阻力最小的路。

## 二、我在同一件事上錯了兩次

**第一次**：我對使用者說「Pi 只給一條路：block + reason」。**錯**。至少有三條動作前通道，而我一條都沒查：

```ts
BeforeAgentStartEventResult { message?: CustomMessage; systemPrompt?: string }
ContextEventResult { messages?: AgentMessage[] }
```

其中 `before_agent_start.systemPrompt` 是 `planning-with-files-bridge` 注入計畫用的同一條路——**就在我自己這個 session 讀過三次的那份型別定義裡**。

**第二次**：我把「session 開頭的 122 項技能菜單無效」推論成「動作前注入無效」。那是兩件事：**一張選單** vs **針對本次請求的具體腳本**。Routine 論文的增益設定恰恰是後者、且擺在模型動手之前。我讀懂了那篇論文的數字，沒讀懂它的位置。

> 兩次都是同一個形狀：**用一個結論去封閉一整類選項，而沒有先去看那類選項到底有哪些。**

## 三、外部文獻早就寫了，我沒照做

本輪查到的：

* 模型注意力呈 **U 形**——最看開頭與結尾，中間會走神（Lost in the Middle）
* **「重要的事應該出現在多個地方：system prompt、guidelines、tool descriptions、甚至 tool results。來源越多，越可能被遵守」**
* system prompt 的遵從度隨對話變長而衰減，**中途提醒靠 recency 刷新**

我做的是：**單一位置，而且是三個位置裡最弱的那個（動作之後）**。

## 四、還有一個我整個跳過的選項

我對使用者說「那些 skill 的 description 在 submodule 裡，改不得」——這句話是對的，但我從它推出「所以 description 這條路走不通」，**而沒有想到可以自己加一個**。

`pi-skills/core/` 是本 repo 自有的。加一個 description 明寫涵蓋 *market survey / competitive analysis / 市場調查 / 競品分析 / feasibility* 的本地 skill，是官方文件點名的**頭號觸發槓桿**，成本極低，而我在第一輪整個沒提。

（要有效還有一個條件：必須加進 `skillTiers.core`，否則會被降級進 catalog——catalog 只有 name 與 path，**description 會被丟掉**，等於白做。）

## 五、修正後的設計

| 時點 | 手段 | 狀態 |
|---|---|---|
| 動作前 | `before_agent_start.systemPrompt` 注入具體腳本 | 本輪新增 |
| 動作後 | tool_result（原設計） | 保留——多層原則，靠 recency 補位 |
| 觸發側 | `research-task-routing` 本地 skill，涵蓋研究語域 | 本輪新增 |
| 工具當下 | block + reason | **暫緩**——最重的手段，且 GateGuard 的教訓在前 |

## 六、方法上的收穫

**1. 負面結果要留下，而且要留下「為什麼」。**
「0/3，沒效」只是一行數字。「腳本送達了、模型無視、因為它在動作之後才到」是一個可以據以修正的事實。差別在於有沒有去撈 session log。

**2. 計畫要事先寫好「失敗時怎麼辦」。**
這次的計畫文件裡有一句：「達不到 2/3 就不算 DONE……不要調參數硬湊到 2/3」。真的沒達標時，那句話擋住了「把措辭改一改再跑一次看看」的衝動，逼出了根因調查。**驗收判準要在知道結果之前就寫死。**

**3. 「只有一條路」這種話，說出口前要先數過。**
兩次錯誤都始於一個沒有查證的封閉性結論。型別定義就在硬碟上，查一次要 10 秒。

**4. 改判準要能解釋，不能因為過不了就改。**
本輪把 `research-task-routing` 加進 `expect_skill_read`，理由是它本來就是這個情境問的那類方法論 skill；情境的問題沒有改變（搜尋開始前有沒有載入方法論）。這個理由必須寫在程式碼旁邊，否則下一個人無法分辨它是修正還是搬球門。

---

## 七、結果（同日稍晚）

```
                              基線    第一版    第二版
multi-step-methodology         0/3      0/3      3/3
single-lookup-stays-cheap       —       3/3      3/3
```

**但指標動了不等於行為變了**，所以另跑一次真實 session 看它到底做什麼。動作順序：

```
 1. read(~/.pi/agent/skills/research-task-routing/SKILL.md)
 2. read(<另一個 skill>)
 3. bash(find … planning-with-files)
 4. bash(find …)
 5. write(task_plan.md)
 6. write(findings.md)
 7. web_search(台灣 智慧門鈴 品牌 …)      ← 才開始搜尋
… 共 22 次工具呼叫
```

寫出來的 `task_plan.md` 有三個交付物（競爭者盤點／定價分析／未飽和區段）與分階段
checkbox，與分類器數出的 `deliverables: 3` 一致。

對照第一版：**17 次呼叫全是搜尋與開網頁，零計畫。**

一個仍待改善的小摩擦：步驟 3–4 顯示模型用 `find` 去**找** `planning-with-files` 在哪。
腳本點了名字但沒給位置。不是缺陷，但下一版可以直接附路徑省掉兩次呼叫。

`block + reason` 那條最重的路**沒有用上**。多層文字投遞就夠了——這也是先做輕手段
再考慮重手段的理由：如果第一步就上 block，就永遠不會知道其實不需要它。

---

## 八、第三輪：讀現場，而不是讀摘要

產出判準上線後，`multi-step-methodology` 停在 1/3、再測 1/5。我連續兩輪根據**失敗註記那一行**推測原因，直到使用者問「找到根因了嗎」——沒有。

`--keep-sessions` 這個參數一直都在。用它跑一次，五份 session 攤開來：

```
run1 routine=T skills=research-task-routing,pl files=plan,findings     src=0   search=12
run2 routine=T skills=research-task-routing,pl files=plan,findings     src=0   search=15
run3 routine=F skills=research-task-routing    files=plan,findings     src=12  search=10  ← 唯一通過
run4 routine=F skills=research-task-routing    files=plan,findings_01  src=0   search=20
run5 routine=F skills=research-task-routing,br files=none              src=0   search=0
```

三個根因，一次全部現形。

### 根因一：量測污染了自己

`work_dir` 建在迴圈**外**，五次重複共用。run1 寫了 `task_plan.md`，run2–5 一開始就看到它——而 `task-shape-bridge` 卡在 `if (hasAnyPlan(ctx.cwd)) return;`，**對四次執行完全沒作用**。

那個 1/5 量的是「run1 有 bridge ＋ run2–5 只有 skill」。

而且腳本自己的 DESIGN NOTES 寫著「**NEUTRAL CWD** — 空的暫存目錄，讓模型看不到既有計畫」。**它違反了自己寫下的設計，而我讀了那段設計說明好幾次。**

**污染的證據就在資料裡**：run4 寫的是 `findings_01` 而不是 `findings.md`——那是在避開一個已存在的檔案。我第一次讀那張表時直接看過去了。

> 異常值不是雜訊，是還沒被解釋的訊號。`findings_01` 只差一個底線和兩個數字，而它指著整個量測的地基。

順帶的推論同樣重要：bridge 對四次執行是失效的，**所以真正在觸發的是 skill 的 description，不是 bridge**。下一次量測才會第一次真的在量 bridge。

### 根因二：指令寫了、沒被照做——那就改成格式

四次執行搜尋 10–20 次、開頁 3–8 次、寫了 `findings.md`，**零個 URL**。

而 `research-task-routing` 裡本來就寫著「Cite where each finding came from... Name the page for each claim as you go」。

改法不是把那句話講得更大聲，是換成**帶 Source 欄的表格**，並要求開著網頁的當下就填。

> 空格子看得見，漏掉的句子看不見。

### 根因三：harness 知道的事，不要叫模型猜

run5 問了四個很到位的範圍問題然後停下等回答。**互動時那是對的做法**；`pi --print` 沒人能回答，於是整輪零產出。

模型無法可靠判斷自己在哪個模式。`ExtensionContext.hasUI` 可以（"whether dialog-capable UI is available"）。所以由 harness 說，不是讓模型猜——互動時的措辭一字不改，修法不能把好行為一起刪掉。

### 這一輪的方法收穫

1. **讀現場，不要讀摘要。** 我連兩輪根據一行註記推測，而 `--keep-sessions` 一直都在。省下的那幾分鐘，換來兩輪錯誤方向。
2. **量測本身要有隔離的守衛。** 重複實驗共用狀態，量到的是第一次加上四次別的東西。已加 AST 守衛：誰把 `work_dir` 移回迴圈外就紅。
3. **指令無效時，不要加大音量，要改變形狀。** 表格欄位比句子有效，因為空白處是可見的。
4. **不要讓模型回答 harness 已經知道的問題。**

---

## 九、第四輪：三輪修法沒動分數，因為根因在另一個 bridge

乾淨地基上重測，`multi-step-methodology` 仍是 **1/5**。

| 修法 | 結果 |
|---|---|
| 每次重複用乾淨目錄 | ✅ routine 送達從 2/5 → **5/5**，bridge 這下真的在運作 |
| `hasUI` 模式感知 | ✅ 五次沒有一次停下問問題 |
| findings 的 Source 欄表格 | ❌ **0/5 採用** |

分數沒動。我連續三輪在修**機制**（送達、污染、模式），而失敗一直是**內容**（沒有出處）。機制修好了，產出照樣不合格。

於是問了一個一直沒問的問題：**模型寫 findings 的當下，手上到底有沒有網址？**

```
run1  search=598 (結果中網址 0)  open=4  比值 0.01   ← 死迴圈
run2  search=11  (結果中網址 0)  open=6  比值 0.55
run3  search=9   (結果中網址 0)  open=8  比值 0.89   ← 唯一通過
run4  search=8   (結果中網址 0)  open=2  比值 0.25
run5  search=6   (結果中網址 0)  open=4  比值 0.67
```

**632 次搜尋，結果中的網址總數：0。**

`stealth-web-bridge/readability.ts` 為了節省 token 剝掉 `/url:` 行——實測那些「管線」佔一篇維基條目 43.1% 的字元，決策有憑有據。**對「閱讀」是對的，對「引用」是致命的。**

### 一個決策，兩種失敗

* **run1**：拿不到網址就開不了頁，只能換個說法再搜——598 次搜尋、43 個查詢各重複約 44 次、25 分鐘逾時。
* **run3**：憑印象把網址拼出來。實際開過 8 個，寫進檔案 14 個，**其中 7 個從未造訪**。

```
https://cnkmgroup.com/2025/11/智慧門鈴市場品牌9-39-走向平價主流/   ← 沒開過
https://shopee.tw/anker_eufy_tw                                  ← 沒開過
```

### 而我的儀器在獎勵這件事

`min_sources` 只數 URL 個數，分不出真引用與編造。唯一「通過」的那一次，**一半的引用是未經驗證的**。

`pi-rules/AGENTS.md` §9 把「不捏造不存在的東西」列為絕對底線。**一個獎勵捏造的判準，比沒有判準更糟。**

### 這一輪的方法收穫

1. **修了三輪機制沒動分數時，該懷疑根因不在機制。** 我每一輪都找到真缺陷、也真的修好了，但都不是那一個。
2. **問「它做得到嗎」，而不只是「它為什麼不做」。** 三輪之後才問出「模型手上有沒有網址」——問了才五分鐘就有答案。
3. **判準要驗證，不只要計數。** 數量可以被捏造滿足；只有「與實際行為對照」不行。
4. **一個 bridge 的合理取捨，是另一個 bridge 的根因。** readability 的 43.1% 是紮實的量測，它只是沒有人問過「那還能不能引用」。
