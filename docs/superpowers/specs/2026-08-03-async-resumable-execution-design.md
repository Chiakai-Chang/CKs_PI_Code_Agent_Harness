# 設計：非同步背景執行與自動續跑（2026-08-03）

## 問題

慢模型本身不是最大的痛點。**慢又同步**才是。

工作交出去之後如果 agent 只能卡住等待，人類就被綁在螢幕前看它慢——等於同時付出「模型慢」和「人閒著」兩份成本。反過來說，只要 agent 能把長工作交出去、自己靠邊停、完成時自動帶著脈絡續跑，模型慢就只是慢，不會綁架使用者的時間。

Compaction 這一塊已由 `pi-extensions/compact-continuation-bridge` 解決。本設計處理另外兩類：**長時間程式執行**與 **subagent**。

## 已驗證的平台事實

以下三點以實測確立，非推測（spike 記錄見
[docs/retro/2026-08-03-absence-is-not-impossibility.md](../../retro/2026-08-03-absence-is-not-impossibility.md)）：

1. Extension 的 event loop 在 agent 閒置期間**持續存活**，脫離的 `setTimeout` 準時觸發。
2. `pi.sendMessage(msg, { triggerTurn: true, deliverAs: "followUp" })` **可以**從脫離的 callback 喚醒閒置的 agent。實測事件序列：`agent_start → turn_start → [custom message] → assistant 回應 → turn_end → agent_end → agent_settled`。
3. `before_agent_start` 的回傳值除了 `systemPrompt` 還有 `message`；後者送達 LLM 的位置是 context **尾端**而非前綴。

另有兩個既有事件可用：`agent_end`、`agent_settled`（後者代表 Pi 不會再自動繼續，是「該通知人類了」的判斷點）。

**尚未驗證、實作前必須先確認**：Windows 上 `spawn(detached: true)` + `unref()` 是否真能在 tool call 回傳後存活。不得因為「Linux 上是這樣」而假設。

---

## 架構

一個新 bridge：`pi-extensions/async-exec-bridge`。

### 元件

| 元件 | 職責 |
|---|---|
| **三個 tool** | `bg_start` 派工並立即回傳、`bg_status` 查詢、`bg_cancel` 取消 |
| **Job store** | 每個工作一個 JSON 檔：狀態、PID、資源類別、起訖時間、exit code、輸出檔路徑 |
| **GPU 租約** | 鎖檔，帶 PID 與 heartbeat，附過期回收 |
| **前置閘門** | 派工前的硬性檢查，不通過就拒絕 |
| **思考步驟** | 派工後注入結構化狀態，強制模型決定停或續 |
| **結果信封** | 有上限的完成通知 |

### 為什麼狀態寫檔而非記憶體

v1 只支援「同一個 session 存活期間」。但狀態一律落地檔案，這樣第二階段（關掉終端機再回來）只需要新增一個讀同一批檔案的 daemon，不必重寫。

同時這也是崩潰復原的基礎：Pi 被砍時沒有任何 handler 會跑，只有磁碟上的狀態能撐過去。

### 資料流

```
模型呼叫 bg_start
  → 前置閘門檢查
      ├─ 不通過 → 回傳拒絕與原因，不派工
      └─ 通過   → （需要時取得租約）→ detached spawn → 寫 job 檔
  → 回傳 handle + 結構化狀態區塊
  → 模型決定 PARK 或 CONTINUE
  ...
工作結束
  → 寫結果檔（先落地）
  → 釋放租約
  → 送出信封（ctx 存活時；idle 則帶 triggerTurn）
  → agent 醒來續跑
```

---

## 資源模型

### 單一軸線

唯一有意義的區分是**這個工作碰不碰本地模型**：

| `localModel` | 例子 | 行為 |
|---|---|---|
| `none`（預設） | `npm test`、`cargo build`、`git push`、網頁抓取、雲端模型 subagent | 可重疊 |
| `shared` | 打同一個正在跑的 llama-server 的 subagent | 允許，但會拖慢 agent 自己的 decode |
| `exclusive` | 需要載入第二個模型 | **拒絕**，不排隊 |

`shared` 不是理論類別。現有的 `deep-research-bridge` spawn 子 `pi` 進程，那些子進程打的就是同一個 endpoint；在 `-np 1` 之下會在 server 端排隊。這個情況本來就存在，只是沒被命名。

### 為什麼 `exclusive` 是拒絕而非排隊

在參考機器上，常駐模型佔 80.76 GiB，GPU carve 為 96 GiB。任何第二個本地模型都塞不進去——不是要等，是永遠等不到。排隊只會製造死鎖。

拒絕時必須回傳可行替代：改用 `shared`、改用雲端模型、或先停掉主 server。

### 兩道硬性閘門

- **租約檔**：管理 bridge 自己派出的工作，避免兩個 `exclusive` 同時啟動。
- **前置探測**：檢查機器上不歸 bridge 管的東西（主 server、殘留進程）。這是資源感測，但**只用來擋掉必死的派工，不做動態決策**。

硬約束不可被模型推理繞過。GPU 租約若只是「建議」，一次判斷失誤就是 OOM 或整台卡死。安全不變式必須由機制強制。

---

## 思考步驟

機制先把不可行的選項移除，模型才在剩下的合法空間內判斷。注入的是結構化事實，不是敘述：

```
[bg] dispatched job a3f1 · "run integration suite" · localModel=none
[bg] running: 1    local model owner: main-server (resident 85.6 GiB)
[bg] GPU headroom: 10.4 GiB / 96 GiB carve
[bg] your context depth: ~18K  (prefill here ~30 t/s, was 98 t/s at 4K)
Decide in one line: PARK (end turn, resume on completion) or CONTINUE (say what you'll do).
```

模型不必猜測資源狀態——那是事實，已經給它了。它判斷的是「這件工作要八分鐘，我手上三件獨立的事，值不值得現在開一件」。

最後一行的 context 深度是刻意放的：讓模型知道「繼續做別的事」會把自己的 context 推深，使下一次 prefill 更貴。深度成本因此進入決策，而不是停留在文件裡的一句建議。

**思考一定要做，但要便宜。** 注入的是幾行事實，期待的回應是一行決定加一句理由，不是自由發揮的長推理。

---

## 錯誤處理

原則：**先把結果寫到磁碟，再嘗試喚醒。** 喚醒可以失敗、可以重來；狀態不行。

| 失效 | 偵測 | 回應 |
|---|---|---|
| 工作非零退出 | exit code | 正常路徑，信封帶 exit code 與尾段輸出 |
| 工作卡死 | per-job timeout | 殺整棵進程樹、釋放租約、信封標 `timeout` |
| Pi 正常結束 | `session_shutdown` | 回收自己派的工作、釋放租約 |
| Pi 崩潰或被砍 | 沒有 handler 會跑 | 下次 `session_start` 對帳：`running` 但 PID 已死 → 標 `orphaned`、釋放租約 |
| 孤兒佔資源 | 租約 PID 死亡或 heartbeat 過期 | 回收。在 `session_start` 與每次前置檢查前各跑一次 |
| 喚醒訊息沒送達 | — | 結果已在磁碟；`bg_status` 可查；`session_start` 對帳時**主動注入**待確認的信封 |
| 結果太大 | 位元組上限 | 沿用 `appendBounded(..., "tail")` 的模式但**用自己的上限**（見〈起始參數〉）；完整輸出留磁碟，信封只帶路徑 |
| 多個工作同時完成 | 碰撞才合併 | 立刻送出；若送出後又有工作完成，併進下一封。**不使用固定去抖動視窗**，那會拖慢單一快速工作 |
| agent 正在跑時工作完成 | `ctx.isIdle()` | 用 `followUp` 但**不帶** `triggerTurn`，等它自然 settle |
| 與 compaction 續跑撞車 | 信封帶 job id | 冪等：同一 job 的信封已送過就不重送 |
| 檔案寫到一半 | — | 原子寫入（temp + rename） |

### Session 替換的生命週期

`/new`、`/resume`、`/fork`、`/clone` **全都**觸發 `session_shutdown` → `session_start`。session 替換是常態，不是邊緣情況。

捕獲的 session-bound 物件（`ctx`、`pi`）在替換後會拋錯。因此：

- 註冊**冪等**的 `session_shutdown` handler，設定 dead 旗標並清除所有 timer。
- 每個 timer 觸發時先檢查 dead 旗標，為真則只寫磁碟、不碰 `ctx` 或 `pi`。
- 工作狀態留在磁碟，由**新** session 的 `session_start` 對帳撿回。

### 進程樹必須殺乾淨

Windows 上 `kill(pid)` 不會殺子進程，必須走 job object 或 `taskkill /T`。

這不只是清理問題。實際案例：一個背景基準測試進程在父任務回報完成後仍握著 82.52 GiB 顯存，導致下一次執行失敗於 `ErrorOutOfDeviceMemory`——**讀起來像「這個設定不受支援」，實際是資源被自己的殘留進程佔走**。租約回收因此也是避免把資源競爭誤診成功能缺陷的機制。

### 刻意不處理

模型若一直選 `CONTINUE` 從不 `PARK`，那是行為問題而非機制問題。用**併發工作數上限**兜住（超過即只能 PARK），其餘交給既有的 loop guard，不在此重造。

---

## 測試策略

| 層級 | 測什麼 | 怎麼測 |
|---|---|---|
| 平台假設 | `detached` spawn 在 Windows 存活、`triggerTurn` 喚醒、timer 跨 idle 存活 | 一次性 spike（後兩項已完成） |
| 純函式 | 資源分類、信封裁切、租約過期判定、job 檔序列化 | 單元測試，不需要 pi |
| 租約 | 併發取得、PID 死亡回收、heartbeat 過期回收 | 單元測試加假 PID |
| 對帳 | `running` 但 PID 已死 → `orphaned`；已完成未確認 → 注入 | 預先擺好 job 檔後跑 `session_start` |
| 生命週期 | session 替換後舊 timer 不拋錯 | 起 session、派工、`/new`、確認無例外且工作被新 session 撿到 |
| 端到端 | 派工 → 靠邊停 → 完成 → 自動續跑 | `--mode rpc` 加撐住的 stdin 加 log 檔（spike 骨架可沿用） |

**明確不測**：模型 PARK/CONTINUE 決策的品質。那是 prompt 工程而非機制正確性，用測試釘死只會綁死後續調整。機制要保證的是「無論模型選什麼都不會壞」。

**回歸基準**：端到端測試須記錄「派工到續跑」的牆鐘時間。日後改動若使其變長，代表喚醒路徑上多了不該有的東西。

---

## 範圍

### v1 包含

- 三個 tool、job store、租約、前置閘門、思考步驟、結果信封
- session 存活期間的非同步執行與自動續跑
- 崩潰後的對帳復原

### v1 不包含

- **跨 session 存活的 daemon**（第二階段；狀態已落地檔案，屆時只需新增讀取者）
- 工作之間的相依關係與 DAG 排程
- 多工作優先權
- 修改 `planning-with-files-bridge` 的注入通道（獨立議題，見
  [docs/retro/2026-08-03-prefix-stabilization-has-a-price-tag.md](../../retro/2026-08-03-prefix-stabilization-has-a-price-tag.md)）

### 起始參數

以下為起始值，實作後依實測調整；均不影響架構決策。

| 參數 | 起始值 | 理由 |
|---|---|---|
| per-job timeout | 30 分鐘，可逐工作覆寫 | 長於一般 build/test，短到不會讓 session 無限掛著。`deep-research-bridge` 的子 agent 用 15 分鐘（`CHILD_TIMEOUT_MS`），背景工作放寬一倍 |
| 併發工作數上限 | 3 | 足夠平行推進獨立工作，又能讓狀態區塊維持在幾行內可讀；超過即只能 PARK |
| **信封注入上限** | **尾段 4 KiB** | **注意：不可沿用 `MAX_CHILD_STDOUT`（8 MiB，`research.ts:179`）——那是擷取上限，不是注入上限。8 MiB 進 context 是災難** |
| 完整輸出擷取上限 | 沿用 `MAX_CHILD_STDOUT` = 8 MiB | 落地磁碟，信封只帶路徑 |
| heartbeat 間隔 | 10 秒 | 過短徒增 I/O |
| 租約過期門檻 | 60 秒無 heartbeat | 過短誤殺尚在啟動的工作，過長讓孤兒佔資源太久 |

### 前置閘門的具體檢查項

`bg_start` 派工前依序檢查，任一不過即拒絕並回傳原因：

1. **併發數**：目前 `running` 工作數 < 上限。
2. **租約回收**：先掃一次租約檔，PID 已死或 heartbeat 過期者釋放。
3. **`localModel: exclusive` 專屬**：
   - 租約無人持有；
   - GPU 已用量低於門檻（代表沒有常駐模型）。以介面卡已配置記憶體對照乾淨基準值判定，而非單看回報的可用量。

第 3 項在常駐模型存在時必然失敗，這是預期行為——回傳拒絕與三個可行替代（改 `shared`、改雲端模型、先停主 server），不排隊。
