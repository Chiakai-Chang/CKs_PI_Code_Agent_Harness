# 佇列推進器:第一次真實量測

**日期**: 2026-08-06
**任務**: `02_Task_Queue/Task_002_advancer_measurement`(佇列被 gitignore,故結論抄錄於此)
**指標定義來源**: `docs/mece/rounds/2026-08-06_round10_SWOT_TOWS_推進器.md`

---

## 結果

| 指標 | 值 |
|---|---|
| 推進次數 N | **3**(第 4 則是升級,不計入) |
| 狀態前進次數 M | **0** |
| **遵循率 M/N** | **0.00** |

魔鬼代言人在 roadmap 裡下的注 ——「第一次不會是 1.0」——**贏了。**

## 但這個 0 的意義必須精確

**機制成立。** 真實 Pi session,cwd 為專用 fixture 專案:

```
 9  CUSTOM[case-advance]  下一步:把 Task_001_probe/status.txt 改成 IN_PROGRESS(§6 step 1)
10  ASSISTANT  bash                     ← 注入觸發了新的一輪
21  CUSTOM[case-advance]  (同一步,第二次)
22  ASSISTANT  bash,bash
34  CUSTOM[case-advance]  (同一步,第三次)
35  ASSISTANT  bash
38  CUSTOM[case-advance]  同一步 3 次沒前進 → 停止推進,請改 ESCALATED
```

三次推進 + 一次升級,**與設計的預算分毫不差**。`harnessRoot()` 在 Pi 下解析得到、旗標讀得到、
`followUp + triggerTurn` 每次都真的產生新的一輪並帶著工具呼叫。

**模型也不是忽略指令** —— 它每次都開始行動了。

## 0 的真正原因:模型在錯的目錄作業

```
11  RESULT  /d/MyProject/CKs_PI_Code_Agent_Harness/02_Task_Queue/Task_001_queue_advancer
                ↑ 去了 harness 的佇列,不是自己 cwd 的
19  RESULT err=True  C.A.S.E. one-at-a-time guard: Task_002_... is already IN_PROGRESS
36  RESULT err=True  Directory containment (bash): this command writes to /d/MyProject/...
```

**兩個既有守衛正確地擋下了它。** 模型接著要求使用者設 `PI_CWD` —— 而 `PI_CWD`
從未被任何東西設定過,那是它自己推論的。

起因:`settings.env` 有 `PI_HARNESS_ROOT=D:/MyProject/CKs_PI_Code_Agent_Harness`,
而 `case-bridge` 又注入 harness 的絕對路徑。模型看到那些路徑,就把相對路徑解析過去了。

**這是同一個問題今天第三次出現。** 前兩次:
1. 一個 run 被要求改暫存目錄的任務狀態,結果把檔案寫進 harness 的 vendored submodule
2. 同一個 run 先用 `write`(被擋),再用 `bash` 重導向繞過(那個洞後來補了)

## 量測自身的缺陷(差點造成相反的結論)

第一次統計用 `grep -o 'case-advance' "$D"/.sess/*/*.jsonl` —— **glob 多了一層目錄,
而檔案直接放在 `.sess/` 下,所以回傳 0。**

差一步就要宣告「推進器完全不會執行」並依 recipe 升級 —— **一個完全錯誤的結論,而且會
退回去修一個根本沒壞的東西。**

> **規則:看到 0 的時候,先證明工具在「應該有值」的情境下數得出來。**
>
> 這是本 session 第二次。深度閘與產出閘也是先看到 0、先懷疑機制,後來才發現是探針
> 到不了那個條件。

## 旗標處置

| 時點 | `enableCaseAdvancer` |
|---|---|
| 量測前 | `false` |
| 量測期間 | `true` |
| 量測後 | **`false`**,已確認安裝副本讀到 false |

**誠實的限制**:旗標寫在 harness 的設定檔,restore 後對**所有專案**生效。
「在 fixture 量測」只做到 cwd 不在 harness repo,**無法讓旗標只對 fixture 生效**。
本次量測期間約 3 分鐘,任何同時進行的 CASE 專案 session 都會被推進。

## 結論與下一步

* **推進器的機制部分成立**,不需調整上限或升級行為。
* **遵循率 0/3,歸因於 cwd 誤判**,與推進器無關。
* **預設值維持 `false`** —— 本次量測不足以支持開啟。
* **重測的前提是先解決 cwd 誤判**(Task_003):`case-bridge` 注入 harness 絕對路徑時,
  應同時明確宣告「你的工作目錄是 X」。

## 給 C.A.S.E. 上游的兩點回饋

1. **協定假設「一個工作區只有一個佇列」。** 實務上模型看得到多個(自己的、harness 的),
   而協定沒說哪一個是它的。建議 §2 加一句:**佇列位置由當前工作目錄決定,不由 prompt 裡
   出現的任何絕對路徑決定。**
2. **`--queue` 驗證器察覺不到「代理在別人的佇列作業」。** 這次是 harness 的 one-at-a-time
   守衛擋下的。若沒有那個守衛,模型會把 harness 的 `Task_001_queue_advancer` 改成
   `IN_PROGRESS`,而驗證器只能事後發現。

## 重現

```bash
D=$(mktemp -d) && cd "$D" && git init -q
python <harness>/external/Local-Agent-Workspace/scripts/bootstrap.py .
mkdir -p 02_Task_Queue/Task_001_probe
printf 'PENDING' > 02_Task_Queue/Task_001_probe/status.txt
# role.md / recipe.md 各一份最小內容
# 把 harness-config.json 的 enableCaseAdvancer 設 true,restore
pi --print --session-dir "$D/.sess" "這個專案是什麼?簡短說明就好。"
find "$D/.sess" -name '*.jsonl' -exec grep -o case-advance {} \; | wc -l
cat 02_Task_Queue/Task_001_probe/status.txt
# 量完把旗標設回 false 並 restore
```

單次樣本,sampler 為伺服器啟動參數(`--temp 1.0`,見 `docs/measurements/README.md`)。
**這是存在性證據(推進器會開火、會觸發回合、會依預算升級),不是頻率證據。**
