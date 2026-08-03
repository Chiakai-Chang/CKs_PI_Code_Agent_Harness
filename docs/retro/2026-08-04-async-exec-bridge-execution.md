# 復盤：async-exec-bridge 從計畫到落地（2026-08-04）

前一份交接（[2026-08-03](2026-08-03-handoff.md)）刻意把「計畫寫完、一行未實作」
的狀態交給乾淨 session，用意是**實測計畫是否真的自足**。這份記錄那個實驗的結果。

結論：計畫的**結構**自足，計畫的**事實**不自足。11 個任務的切分、介面、測試意圖
全部可以照著做；但計畫裡的 Pi API 幾乎整段是錯的，而且錯得很像對的。

---

## 一、計畫是照著一個不存在的 API 寫的

開工前的審查（比對**安裝版**
`@earendil-works/pi-coding-agent/dist/core/extensions/types.d.ts`）找出七個會直接
壞掉的缺陷。它們共同的形狀是：**看起來很合理的 API**。

| 計畫寫的 | 實際 |
|---|---|
| `pi.registerTool("bg_start", { description, handler })` | `registerTool(tool)` 單一物件，必填 `name`/`label`/`parameters`(TypeBox)/`execute(id, params, signal, onUpdate, ctx)` |
| handler 回傳字串 | 必須回傳 `AgentToolResult`：`{ content: [{ type: "text", text }] }` |
| （沒有 `parameters`） | 沒有 schema 的工具**收不到任何參數**，模型無從指定要跑什麼 |
| `session_start` 回傳 `{ message }` | 該 handler 的 `R = undefined`，**回傳值直接丟棄** |
| `ctx.getContextUsage()?.usedTokens` | 實際是 `{ tokens, contextWindow, percent }` |
| `ENVELOPE_TAIL_BYTES` | 用到但沒 import |
| `CLEAN_BASELINE_GIB` | 用到兩次，整份計畫都沒定義 |

第四項最值得記：`session_start` 那段程式碼在回傳前已經把 pending job 標成
`acknowledged: true`。也就是說**規格裡「喚醒訊息沒送達 → 下次啟動主動注入」那條
復原路徑，不只是無效，還會把通知永久吃掉**。一個「回傳值被忽略」的型別細節，
足以把復原機制反轉成資料遺失機制。

### 學到的

**計畫審查要查的不只是邏輯，是它引用的每一個外部事實。** 前一個 session 做了四輪
多角色審查，四輪都沒抓到——因為四輪都在審**推理**，而缺陷在**引用**。API 形狀不是
推理問題，是查表問題，而沒有人去查那張表。

規則：**計畫裡出現的每一個第三方 API 呼叫，都要在動手前對照安裝版的型別定義**，
不是文件、不是記憶、不是別的 bridge 的用法（別的 bridge 也可能是對著舊版寫的）。

---

## 二、三個缺陷是被「跑一次」抓到的，不是被審查抓到的

### 1. 一個永遠不會失敗的檢查（e2e 腳本自己）

計畫裡的 `e2e-check.sh` 帶著一句自我提醒：「A check that only prints is a check
that never fails.」——然後它自己就是那種檢查：

```bash
turns=$(grep -oc '"type":"turn_end"' "$LOG" || echo 0)
```

`grep -c` 沒有比對到時會**印出 0 並且以 1 結束**，所以 `|| echo 0` 又補一個 0，
變數成了兩行的 `"0\n0"`；`[ "$turns" -lt 2 ]` 於是死在 `integer expected`，
`if` 把錯誤當成 false，一路掉到最後印出 **PASS**。

第一次執行的真實輸出：

```
turn_end=0
0  async-exec messages=0
0
e2e-check.sh: line 20: [: 0
0: integer expected
PASS
```

**它在測到零的情況下宣告通過。** 而且同一支腳本還把提示詞當成位置參數傳給
`pi --mode rpc`——rpc 的協定是 stdin 上的 `{"type":"prompt","message":...}`，
位置參數會被忽略，所以那個零是真的：根本沒有任何 turn 跑過。

### 2. 通知會把上一次執行的工作算進來

修好腳本、跑出真 PASS 之後，日誌裡的通知寫著：

```
[async-exec] 2 background job(s) finished, 0 not clean.
```

那次只派了**一個**工作。第二個是前一次執行留在 `.pi/async-exec/` 的紀錄——
`agent_settled` 的判斷讀的是磁碟目錄，而 job 檔會活得比 session 久。規格
第 §通知 條寫的是「**本 session** 至少有一個背景工作完成過」，實作卻讀成了
「這個目錄裡曾經有工作完成過」。照這個寫法，**只要你曾經用過一次背景工作，
之後每一次普通對話結束都會打擾你**，正是規格明文要避免的那件事。

改成只計入本 session 看見完成的工作（含由 `before_agent_start` 補報的崩潰復原
工作）。修完重跑，通知正確變成 `1 background job(s) finished`。

### 3. `uninstall.py` 的受管 bridge 名單漂移了七個

這個與本次功能無關，是順帶撞見的既有缺陷：`restore.py` 管 11 個 bridge，
`uninstall.py` 的 `MANAGED_BRIDGES` 停在 5 個。因為 **Pi 是依目錄自動探索
`~/.pi/agent/extensions/*/`**，解除安裝留下的 7 個目錄**仍然每次啟動都被載入**。
使用者以為移除了，實際沒有。

repo 早就有 `TestManagedSkillsConsistency` 在鎖 skills 名單——**唯獨 bridges 沒有
對應的守衛，所以它漂移了，而且沒有人知道**。已補上 `TestManagedBridgesConsistency`，
一次鎖住四份名單（`restore.py` 兩份、`uninstall.py` 一份、`bridge-manifest.json`
一份），並實測讓它失敗過一次以確認它抓得到。

### 4. 合併後的自我複查又抓到三個（同一個形狀）

已合併、已推送之後再讀一次程式碼，又找到三個——**全部落在 e2e 沒有走過的路徑上**：

* **`agent_settled` 會無限重複通知。** `finishedThisSession` 從不清空，所以背景工作
  完成之後，**該 session 之後每一次回合結束都會再通知一次同一件事**。e2e 沒抓到，
  因為它在續跑那一輪之後就結束了——**只 settle 過一次**。這跟前面修掉的「算進上一次
  執行」是同一條規則被違反兩次，只是層級不同。
* **崩潰時剛好完成的工作被誤報為 `orphaned`。** `reconcile` 只看 pid 死了就標
  orphaned，沒有去讀 shell wrapper 已經寫好的 `.rc`。那是崩潰唯一留下的證據，
  而且會把一次乾淨成功報成失敗。
* **e2e 腳本對「已安裝的使用者」是壞的。** 它用 `-e <repo 路徑>` 啟動，而安裝版會被
  Pi 依目錄自動探索，於是 `bg_start` 註冊兩次，**Pi 直接拒絕啟動**：
  `Tool "bg_start" conflicts with ...`。先前會 PASS 純粹因為當時還沒安裝過。
  這正是 `TestExtensionsNotDoubleRegistered` 記錄過的老坑，只是換個入口重演。
  已改為**不帶 `-e`、直接測安裝版**——那才是使用者真正載入的東西。

前兩個修法都不是在 wiring 裡加 if：`settleNotification()` 移進 `notify.ts`（7 個測試）、
`reconcile()` 改為注入 `readCode`（8 個測試）。原本用字串比對 wiring 的 Python 測試
因此失效——這剛好說明了那種測試的脆弱：**它測的是寫法，不是行為**。

### 學到的

**「跑一次」抓到的三個缺陷，沒有一個是審查形狀能抓到的**，因為三個都需要
**觀察實際輸出**：一個要看 shell 的退出碼語義，一個要看數字對不對，
一個要看 `~/.pi/` 目錄裡真的剩下什麼。

延伸出一條更尖的版本：**看到 PASS 不等於驗證完成，還要問「這個檢查有沒有可能
印出 FAIL」**。這次是靠故意讓守衛失敗一次來確認的，兩個新守衛都做了這件事。

---

## 三、可用的方法：先證明儀器會壞

Task 11 卡在模型 server 沒開時，先做了一件不需要模型的驗證：確認 bridge 在
**Pi 自己的 loader** 底下能載入。但「沒有錯誤訊息」本身不是證據
（見 [absence-is-not-impossibility](2026-08-03-absence-is-not-impossibility.md)），
所以先把 bridge 複製一份到暫存目錄、加上一行 `throw`，跑同一個指令：

```
Error: Failed to load extension "...\aeb\index.ts": Failed to load extension: AEB-LOAD-PROBE
```

儀器會壞，於是真檔案的乾淨載入才是證據。這也順帶證明了 `registerTool` 接受了
三個 schema——schema 有問題會在模組求值期就丟出來，而那條路徑剛剛示範過會現形。

同樣的手法用在兩個新守衛上（改壞名單、確認測試變紅、改回來）。
**這一步很便宜，而且是「PASS 到底代表什麼」唯一的答案。**

---

## 四、實測數字（2026-08-04，本機）

模型 server：`GRM-3.2-Sky-OPAL-balanced.gguf`，Vulkan，`-c 262144`，`-np 1`
（`/props` 回報 `total_slots: 1`，因此 bridge 預設 `PI_MODEL_SERVER_SLOTS=1` 是對的讀法）。

```
派工到自動續跑        52 秒（其中工作本身 20 秒）
turn_end              3（派工、PARK、續跑）
工作結果              exit=0，22.2 秒，尾段 "DONE"
續跑後模型的最後一句  "Nothing further to do."
通知                  "1 background job(s) finished, 0 not clean."（**恰好一次**）
```

（此為修完上述三個缺陷後、**對安裝版**重跑的數字。修正前對 repo 檔案跑出的是 32 秒；
兩者不可直接比較，因為受測對象與模型當下負載都不同。牆鐘數字只作為日後**相對**回歸
基準，不是硬指標。）

事件鏈與規格一致：`bg_start` 回傳狀態區塊（含**真實** context 深度 ~16K，
不是佔位的 0）→ 模型 PARK、該輪結束 → 工作完成 → 信封以 `followUp` +
`triggerTurn` 喚醒 → 第三輪讀尾段並收工 → `agent_settled` 通知人類。

冷路徑也實測過：跑 `python scripts/setup.py --mode restore` 後，
以**安裝版**（不帶 `-e`）啟動 Pi，模型成功呼叫 `bg_status` 並取回真實紀錄。

---

## 五、v1 明確沒做（不是遺漏，是範圍）

- **跨 session 常駐 daemon**。狀態已落檔，v2 只需新增讀取者。
- **即時 GPU 探測**，連帶 `localModel: "exclusive"` 目前直接拒絕。
  `preflight` 的真正閘門已實作且測試通過，v2 只要供給探測值並移除早退。
- **`lease.ts` 是刻意的死碼**：完整實作、8 個測試通過，但 v1 不發 `exclusive`，
  所以永不取得租約、`beat()` 永不呼叫。不要刪，也不要接一個無事可做的 heartbeat。
- **per-job timeout 覆寫**：規格說「可逐工作覆寫」，實作只有全域 `JOB_TIMEOUT_MS`。
- **`pi-telegram` 旁路通知**：規格列為選用，未實作，目前只有 `ctx.ui.notify`。
- **server slot 自動偵測**：目前讀環境變數。但這次順帶確認 llama-server 的
  `/props` 會回報 `total_slots`，所以 v2 可以直接問，不必要求使用者設對。
- **session 替換（`/new`、`/fork`）的生命週期實測**：只有程式上的 dead 旗標與
  timer 清除，沒有真的起一個 session 派工再 `/new` 驗過。

## 五之二、合併後複查列出的四項，全部已處理

### 1（已修）保留策略：保守預設

已回報且已完成的紀錄保留 **7 天**、最多 **50 筆**，超出者由舊到新連同 `.out` / `.rc` /
`.pid` 一併清除。**執行中、以及尚未回報過的完成結果永不清除**，不論多舊——後者正是
崩潰復原的通知本身，刪掉它就是這整套「先落檔再喚醒」設計要防的資料遺失。清理排在
`session_start` 的對帳**之後**，所以不會刪掉還沒被讀到的結果。判斷邏輯在
`retention.ts`（7 個測試），刪檔在 `jobs.ts` 的 `deleteJob()`。

### 2（已修）`tailBytes` 現在真的以位元組計

原本以 JS 字串長度切，所以名為 `ENVELOPE_TAIL_BYTES` 的 4 KiB 預算，遇到中文輸出
實際會注入約 3 倍。改為以 UTF-8 位元組計，取尾段後把起點往後推過所有接續位元組
（`10xxxxxx`）對齊到字元邊界——這同時讓 emoji 之類的增補平面字元不會被切半。
以 120 種不同的位元組偏移對純中文檔案掃過一遍，無亂碼、無超量、結果恆為原字串的後綴。

順帶修掉同一條路徑上的浪費：`envelopeFor` 原本把整份擷取檔（上限 8 MiB）讀進字串
只為了留 4 KiB。改為 `capture.ts` 的 `readTail()` 直接 seek 到檔尾。**對齊必須在
解碼前對原始 buffer 做**——先解碼會把被截斷的字元變成 `U+FFFD`，而那個 3 位元組的
替代字元塞得進預算、能活過後續任何裁切。

### 3（已修）先寫紀錄再 spawn，而且工作自己記下 pid

`bg_start` 現在先寫一筆 `pid: null` 的紀錄才 spawn；shell wrapper 的第一件事是把
自己的 pid 寫進 `job-<id>.pid`。崩潰視窗因此從兩邊都被關上：紀錄一定存在，pid 由
工作自己從內部留下。

**`echo $$` 在 Windows 上是錯的。** Git Bash（MSYS）的 `$$` 是 MSYS pid，與 `spawn()`
回傳、`taskkill` 和 `process.kill` 使用的 Windows pid 是**不同的命名空間**——同一個
行程實測為 1388 對 17924。MSYS 在 `/proc/<pid>/winpid` 提供對照，真正的 POSIX 機器上
該路徑不存在而 `$$` 本來就對，所以兩邊都用同一段條件式處理。

再往下還有一層：**記下的 pid 不會等於 `spawn()` 回傳的那個**。Windows 上
`Git/bin/bash.exe` 是個啟動器，Node 拿到的是外層 wrapper（實測 23240），真正執行工作
的 shell 是另一個行程（11804）。所以測試改為驗**真正需要的性質**——記下的 pid 是活的、
而且 `killTree` 殺得掉它——而不是驗一個永遠不會成立的等式。

### 4（已修）PID 重用：驗身分，不只驗存在

`process.kill(pid, 0)` 只回答「有沒有行程叫這個號碼」。工作結束後，作業系統可以把
那個號碼發給任何人，於是**已完成的工作永遠讀作「還在跑」**（佔著併發名額不放），
更糟的是 **`bg_cancel` 會對一個無辜的陌生行程執行 `killTree`，連它整棵樹一起殺掉**。

修法是比對**行程啟動時間**與工作派出時間：工作自己的行程在派工後幾毫秒就起來，
啟動時間若晚於 `startedAt + 60 秒`，那就是別人。不需要在紀錄裡新增欄位——
`startedAt` 本來就有。

取得啟動時間的手段依平台而異，且都不便宜：

* **Windows 沒有 `/proc`，而且 `wmic` 已經不在了**（本機 Windows 11 26200 實測 absent），
  所以走 PowerShell。用 `Get-Process` 而不是 `Get-CimInstance`：後者的 `CreationDate`
  回傳的是**當地語系化字串**（在本機主控台直接是亂碼），前者的
  `.StartTime.ToUniversalTime().ToString('o')` 是 `Date.parse` 吃得下的 ISO-8601。
* 每次約 **0.34 秒**。

這個成本決定了它能放在哪裡，而不是反過來：

| 位置 | 用哪個檢查 | 理由 |
|---|---|---|
| `session_start` 對帳 | `isSameProcess`（貴） | 每個 session 只跑一次 |
| `bg_cancel` | `isSameProcess`（貴） | 使用者觸發，且這是會誤殺別人的那條路徑 |
| 2 秒輪詢 | `isAlive`（便宜） | 0.34 秒的探測不可能每 2 秒跑一次 |

輪詢因此改為**先讀 `.rc`**：那是 wrapper 自己聲明「我做完了」，比問 pid 可靠。
否則被重用的號碼會讓已完成的工作一路「執行中」到 30 分鐘逾時為止。

還有一個 API 形狀上的收穫：`reconcile` 的第二個參數從 `(pid) => boolean` 改成
`(job) => boolean`。**「這個工作還在跑嗎」是工作層級的問題，不是 pid 層級的**——
要分辨自己的行程和一個借用了號碼的陌生人，就必須看得到工作的派工時間。
型別本身把這件事講清楚了。

無法判定啟動時間時（探測失敗、平台不給）退回「存在即視為同一個」：把一個**真的還在跑**
的工作誤判成死掉，比多留一筆紀錄更糟。

剩下的都是規格列出、v1 明確不做的範圍項（見上節）：per-job timeout 覆寫、
`pi-telegram` 旁路通知、session 替換（`/new`、`/fork`）的生命週期實測。
以及 e2e 因需要模型而不在 CI。

## 六、安全，說清楚

`bg_start` 執行**任意 shell 指令、detached、無確認**，而且**活過 agent 被中止**。
中止 agent 不會中止它派出的背景工作。這既是功能價值也是風險，同源。

v1 靠 `bg_cancel`（殺整棵進程樹）、`session_start` 對帳、磁碟稽核軌跡兜住。
**沒有 allowlist、沒有確認提示。** 要接不受信任的提示來源，先加。
