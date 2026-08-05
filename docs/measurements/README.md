# Measurements

Baselines produced by `scripts/measure-triggers.py --report`. Each line is one
run: date, scenario pass rates, and the notes from failing runs.

These exist so a prompt or routing change can be compared against what was there
before, rather than validated by a single manual run. Every prompt-shaping
decision in this harness was tuned blind until this file existed.

`trigger-baseline.jsonl` is append-only. Do not rewrite past entries — a baseline
that gets edited to match the current build is not a baseline.

## 判準演進（2026-08-05）

```
run1  activation 0/3   第一版路由：動作後投遞（tool_result）
run2  activation 3/3   第二版：動作前（before_agent_start）+ research-task-routing skill
run3  outcome    0/3   判準換成產出，但只讀聊天回覆 —— 量錯地方
run4  outcome    1/3   判準修正：答案 + 寫出的檔案
```

**run2 → run3 的落差是判準變嚴，不是退步。** activation 問「有沒有載入方法論」，
outcome 問「三個交付項有沒有涵蓋、有沒有至少兩個不重複來源」。前者 3/3 的那一版，
用後者量是 0/3——聊天回覆裡零個連結。

**run3 → run4 是修正我自己的量測錯誤。** 實測顯示模型引用了十個來源，寫在
`findings.md`——那正是 `planning-with-files` 規定 findings 該去的地方。只讀聊天回覆的
判準，恰好懲罰了正在被推動的那個行為。交付物是「答案 + 產出的檔案」。

## ⚠️ run1–run4 的數字有污染，不可直接比較

`work_dir` 原本建在重複迴圈**外**，五次共用。run1 寫了 `task_plan.md`，
run2–5 一開始就看到它，而 `task-shape-bridge` 卡在 `hasAnyPlan(cwd)`——
**對後四次完全沒作用**。

所以 run4 的 `1/5` 量的是「run1 有 bridge ＋ run2–5 只有 skill」。
污染的痕跡就在資料裡：其中一次寫的是 `findings_01` 而不是 `findings.md`。

2026-08-05 起每次重複用乾淨目錄，並有 AST 守衛擋住它被移回迴圈外
（`TestRepeatsAreIndependent`）。**修正後的第一筆數字才是第一次真的在量 bridge。**

## 舊的殘餘缺口（保留原文，作為當時判讀的記錄）

`multi-step-methodology` 產出判準 **1/3**。三次中兩次失敗，且都是 0 個來源。

其中一次（run2）讀了 7 次 SKILL.md，但讀的是 `~/.agents/skills/research/`——
**鄰居工具安裝的另一個 research skill**，不在本 harness 的 manifest 裡也不是 junction，
但 Pi 看得到（`.agents/skills/` 是跨工具通用位置）。它的 description 針對
「research a topic」寫得很直接，與 `research-task-routing` 搶同一類請求。

**不打算靠把描述寫得更強勢去搶。** 那是軍備競賽，且等於把使用率當目標。

## n=3 的解析度

本機模型 temperature 0.6。1/3 與 2/3 在三次取樣下分不開。要宣稱任何調整有效，
`--repeats` 需提高到 5 以上，否則量到的是雜訊。


## 根因：搜尋結果沒有網址（2026-08-05 已修）

三輪修法都沒動到分數，因為根因在另一個 bridge。

```
run1  search=598 (結果中網址 0)  open=4  比值 0.01   ← 死迴圈、25 分鐘逾時
run2  search=11  (結果中網址 0)  open=6  比值 0.55
run3  search=9   (結果中網址 0)  open=8  比值 0.89
run4  search=8   (結果中網址 0)  open=2  比值 0.25
run5  search=6   (結果中網址 0)  open=4  比值 0.67
```

**632 次搜尋，結果中的網址總數 0。**

`stealth-web-bridge/readability.ts` 為節省 token 剝掉全部 `/url:` 行——實測那些管線
佔一篇維基條目 43.1% 的字元。決策有憑有據，**對閱讀是對的，對引用是致命的**。

而 `web_search` 的工具說明同時寫著「return result titles, snippets, and **URLs**」
與「call web_open on the 1-3 most relevant **result URLs**」——**它宣稱回傳網址、
實際剝掉、然後叫模型去開那些它從未拿到的位址**。模型憑印象拼位址是被這條指令逼出來的。

### 修法與成本（實測，非估計）

保留「連結區塊內同時有 heading」的 `/url:`（＝結果連結），其餘照舊剝除：

```
                    /url 全留    只留標題型
wikipedia article     43.1%   →     0.0%   (0/44)
docs site             11.4%   →     0.0%   (0/158)
github issue          28.0%   →     0.0%   (0/110)
news homepage         16.8%   →     5.3%   (42/112)
```

**當初那 43.1% 完全不受影響**——文章的連結是內文連結，沒有 heading。索引/搜尋型
頁面付 5.3%，換回可引用的位址。實測新聞首頁 34,012 → 20,804 字元、保留 43 條位址。


## ⚠️ run1–run7 的分數不可比：live 評分與 session 檔不一致（2026-08-05 已修）

一次量測回報 **3/5**，用同一支 `judge` 對同樣五份 session 重評卻是 **0/5**。

原因：`run_once` 從 `pi --print --mode json` 的 **stdout 串流**收集資料，而那份串流
比 session 檔少東西。少掉的正是寫進檔案的引用——於是 live 端只看到少數幾個
「都開過」的網址就放行，放過了三次分別捏造 5、5、13 個引用的執行。

已改為**從 session 檔評分**（`parse_session` / `newest_session`）。session JSONL 是
那次執行的正式紀錄，改用它之後 live 分數與事後重評才會是同一個數字——
**基線要有意義，這是前提**。

因此 `trigger-baseline.jsonl` 裡 2026-08-05 之前的所有 `outcome` 分數都偏寬鬆，
**不可與之後的數字直接比較**。保留不刪，因為它們正是這道修法存在的理由。

### 修正後對同一批 session 的重評

```
run1  FAIL  only 0 verified source(s)
run2  FAIL  only 0 verified source(s)
run3  FAIL  5 cited page(s) were never opened
run4  FAIL  5 cited page(s) were never opened
run5  FAIL  13 cited page(s) were never opened
```

搜尋結果的網址已經修好了（0 → 278 條），死迴圈也沒再出現，**但模型拿到真網址之後
仍然大量引用沒開過的頁面**。那是下一個要查的問題，不是這一輪能宣稱解決的。

## 每個 repeat 現在記錄機制,不只分數(2026-08-06)

baseline 的每個情境多了 `runs` 陣列,一個 repeat 一筆:

```json
{"searches": 6, "opens": 2, "writes": 9,
 "urls_in_files": 10, "urls_opened": 2,
 "guards": {"Citation guard": 2, "[task-shape]": 1}}
```

**為什麼分開記 `urls_in_files` 與 `urls_opened`**:引用閘上線那一輪,run1 開了 2 頁卻寫了
10 個網址。單一個「引用數」欄位會把它記成乾淨的勝利,實際上其中 4 個是編造的購物網站
搜尋端點。

**沒開火的閘記為不存在,不記為 0。** 深度閘與產出閘至今**從未被這支探針到達過**,
列成 `0` 會讀起來像「測過、很安靜」。

**守衛次數只數 `toolResult`。** 直接 grep 原始 session 會把模型自己在文字裡覆述的拒絕也數進去 ——
手數是 `2、1、2`,只數 toolResult 是 `2、1、1`,後者才對(與寫入大小吻合:只有 4524 字元
那次被擋)。

### 判準再次變嚴:`min_artifacts`(2026-08-06)

及格線加上「至少寫出一個檔案,且內容 ≥200 字元」。理由是 session `019fd29d`:
三個 turn 的調查跑完,`write/edit = 0`,工作目錄只剩 `.git`。

**刻意不用「有沒有載入方法論 skill」當判準** —— 那個指標會漂移成「觸發得更頻繁」。
實測也證明它沒有意義:3/3 的 run 都讀了 `research-task-routing`,檔案裡的網址仍是 0/0/0。

**因此 2026-08-06 起的 outcome 分數與之前不可直接比較。**
