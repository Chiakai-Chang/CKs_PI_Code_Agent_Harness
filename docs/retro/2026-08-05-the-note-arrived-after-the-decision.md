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
