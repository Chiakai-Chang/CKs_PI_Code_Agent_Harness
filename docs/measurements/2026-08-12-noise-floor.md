# 噪音底線:同題同臂重複五次(2026-08-12)

**狀態:預先登錄(runs 尚未完成)。** 這一段在跑之前寫完,判準寫在看到數字之前。

## 為什麼

`01_Roadmap/global_dod.md` 第 6 條:

> **判定建立在噪音底線之上**:已量測本機模型的 run 間變異,且樣本數滿足 `n ≳ (sd/(Δ/2))²`
> —— ❌ **未量測**。目前所有結論都建立在 n=2 上

同一份 global_dod 的第 1 條寫著「✅ 2/2(各擋 14 次)。**樣本不足,見第 6 條**」。
也就是說,這個 repo 目前每一條「有效果」的宣稱,都掛在一個自己標記為未量測的前提上。
另一個更具體的觸發原因:同一提示、同一臂,量到過 **42 次 vs 4 次工具呼叫**
(`docs/case/` 的「不能用更多資料把任務變長」)。若真實 sd 是那個量級,
先前所有 n=2 的比較都不成立 —— 不是結論錯,是**還沒有資格下結論**。

## 預先登錄的設計(寫在看到數字之前)

| 項目 | 值 | 為什麼是這個 |
|---|---|---|
| 工具 | `python scripts/measure-advancer.py --runs 5 --prompt research --out …` | 既有工具,計數器經 `--self-check` 對過手工 fixture(7 個計數器) |
| 臂 | `research` 單一臂 | 這是**變異量測不是 A/B**。研究型提示才是效果宣稱發生的地方;`baseline`(「這個專案是什麼」)量到的是地板,不代表宣稱的場景 |
| n | 5 | 腳本自己的 `MIN_RELIABLE_N = 3`;取 5 以便 sd 不是「兩點連一線」 |
| 指標 | `tool_calls`、`blocked`、`advance_injections`、`status_writes_tool`、`assistant_turns` | 腳本固定的五個,不是事後挑的 |
| 主指標 | `tool_calls` | 42 vs 4 就是這一個,也是先前比較最常引用的 |
| Δ | 事後對 Δ=3、5、10 各報一次 `n ≳ (sd/(Δ/2))²` | 不預設「我們想偵測多小的差」;報成一條曲線,讓下一個實驗自己挑 |

**逾時算資料,不算作廢。** `ended` 欄位會記下是正常結束還是撞到上限;
一個撞上限的 run 是「這個配置有時候會跑很久」的證據,把它丟掉會把 sd 洗小
(`probe-fixtures-must-be-rebuildable` 的同一條教訓:timeout counts as fail)。

**不合併不同配置。** `--variance` 依每個 run 自己記下的 `config` 分組,
且**拒絕**把「沒有記錄配置」的舊 run 併進來。

## 配置

* 模型服務:llama.cpp,`C:\models\GRM-3.2-Sky-ONYX-balanced.gguf`,
  `n_slots = 1`、`n_ctx_slot = 262144`、`kv_unified = false`,`http://127.0.0.1:8080`
* 取樣參數(伺服器 `/props` 回報的預設):`temperature 1.0`、`top_k 20`、`top_p 0.95`、
  `min_p 0.0`、`repeat_penalty 1.0`、`seed 4294967295`(隨機)
* **`n_slots = 1`,所以五個 run 必須依序跑**,腳本本來就是依序的
* harness commit:見下方結果段(寫入時填實際值)

**`seed` 是隨機的,這正是要量的東西。** 固定 seed 會把 sd 壓成 0 並製造出
「沒有差異」的假象 —— 與 `sampler-pinning-manufactures-no-difference` 同一個形狀。

## 結果

harness commit `03fc8d4`,五個 run 全部 `ended: finished`,**5/5 走到 REVIEW**,
原始資料:[2026-08-12-noise-floor.results.json](2026-08-12-noise-floor.results.json)

| run | tool_calls | assistant_turns | blocked | advance_injections | status_writes | first_record_s |
|---|---|---|---|---|---|---|
| 1 | 47 | 26 | 23 | 3 | 2 | 50 |
| 2 | 62 | 34 | 25 | 2 | 4 | 50 |
| 3 | **116** | **62** | 18 | 2 | 4 | 65 |
| 4 | 44 | 25 | 10 | 2 | 3 | 65 |
| 5 | 49 | 27 | 18 | 3 | 2 | 75 |

```
config {"enableCaseAdvancer": true}   runs=5
  tool_calls             n=5 mean=63.60 sd=26.91   need_n(Δ=3)=322  need_n(Δ=5)=116  need_n(Δ=10)=29
  blocked                n=5 mean=18.80 sd=5.19    need_n(Δ=3)=12   need_n(Δ=5)=5    need_n(Δ=10)=2
  advance_injections     n=5 mean=2.40  sd=0.49    need_n=1
  status_writes_tool     n=5 mean=3.00  sd=0.89    need_n=1
  assistant_turns        n=5 mean=34.80 sd=13.96   need_n(Δ=3)=87   need_n(Δ=5)=32   need_n(Δ=10)=8
```

### 一句話

**同題、同臂、同配置,工具呼叫數 44 到 116,sd = 26.9(變異係數 42%)。**
換算回來:**n=2 的比較只能偵測到 38 次呼叫以上的差,n=3 只能偵測到 31 次以上。**
這個 repo 過去每一個引用呼叫數差異的比較都是 n=1 或 n=2。

### 三件立刻改變的事

1. **「誤擋多花約十次呼叫(33 vs 23)」不是證據**(PROGRESS.md,n=1 對 n=1)。
   Δ=10 在這個噪音底線下需要 **n=29**。誤擋本身是真的(session log 裡看得到那兩次拒絕),
   **多花的呼叫數量是量不出來的**。
2. **「23–33 → 57」(T-A6 任務變長)勉強站得住,但不是靠 n=1。**
   Δ≈30 落在 n=2~3 的可偵測範圍邊緣;真正撐住這個結論的是**機制**
   (逐次回報的驗證器把一次批次拆成多次),不是那個數字。
3. **`advance_injections`、`status_writes_tool` 幾乎沒有噪音**(sd 0.49 / 0.89)。
   涉及這兩個的宣稱,n=2 就夠 —— **噪音底線不是一個數字,是每個指標一個數字**。

### 那個 outlier 要不要拿掉:不拿

run 3 是 116 次呼叫、62 個回合,把 sd 從 6.87 撐到 26.91。
拿掉它會讓 `need_n(Δ=10)` 從 29 變成 2 —— 也就是把「這個比較做不了」變成「做得了」。

**不拿掉。** 理由不是統計潔癖:這一臂**真的會**偶爾跑出兩倍長的 run,
那正是先前 42 vs 4 的同一件事。丟掉尾巴等於宣告尾巴不存在,
與 `probe-fixtures-must-be-rebuildable`(timeout counts as fail)是同一條紀律。
兩個數字都列在上面,讓下一個人自己看見差別有多大。

### 這個 sd 屬於誰

**屬於這個配置,不屬於這個模型。** 它是在 `measure-advancer.py` 的
research 提示 + 該腳本自己的任務 fixture 上量的。
把它套到 PiTaskLab 的任務或別的提示上,就是這個 repo 一直在防的**借來的數字**
(Harness-Bench:能力是 model–harness 配對的屬性)。

可以帶走的是兩件事,不是那個 26.9:
* **量級**:這個本機模型在多步任務上的呼叫數變異是**幾十%等級,不是幾%等級**
* **紀律**:任何呼叫數差異的宣稱,要嘛附上同臂重複量到的 sd,要嘛改成報機制與結果

### 反過來說,結果指標很穩

`status` 5/5 全是 REVIEW,交付物檔案清單 5/5 完全相同
(`action_log.jsonl`、`output.md`、`planning.md`、`recipe.md`、`retro.md`、`role.md`、`status.txt`)。
**過程指標吵、結果指標穩** —— 這直接說明該用哪一種下判斷:
判 DoD 是否達成(二元、可機械判定),不要判它花了幾次呼叫。
先前那些 11/11、1/11 的計分是對的做法,這一次的量測是它的旁證。
