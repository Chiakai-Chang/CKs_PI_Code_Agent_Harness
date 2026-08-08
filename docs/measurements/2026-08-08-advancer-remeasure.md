# 2026-08-08 推進器重測:儀器建好了,而它量到一個新缺陷

**沒有判定。** `enableCaseAdvancer` 維持 `false`,理由與 2026-08-06 那次**不同**。

| | |
|---|---|
| 模型 | `GRM-3.2-Sky-ONYX-balanced.gguf`,n_ctx 262144,`--temp 1.0` |
| 旗標 | 量測期間 `true`,量完改回 `false` 並確認 `git status` 乾淨 |
| 佇列 | 量測期間**移出 repo**(不是改名 —— 改名留下的目錄上次報廢了一整場 run) |
| 提示 | 基準線,逐字取自 2026-08-06 的紀錄,未改寫 |
| 每次 run | 各自獨立的 temp 目錄 |

## 結果:三次基準線

| run | assistant 輪次 | 工具呼叫 | 擋阻 | **推進注入** | status 寫入 | 終態 | 最後一輪 |
|---|---|---|---|---|---|---|---|
| 1 | 7 | 8 | 1 | **0** | 0 | `PENDING` | **有文字、沒工具** |
| 2 | 2 | 3 | 2 | **0** | 0 | `PENDING` | **有文字、沒工具** |
| 3 | 5 | 4 | 1 | **0** | 0 | `PENDING` | **有文字、沒工具** |

## 這是新缺陷,不是舊結論的重現

推進器的開口條件是 **「這一輪有講話、而且沒有呼叫任何工具」**
(`index.ts` 的 `turn_end`:`if (!spoke || worked) return;`)。

**三次 run 的最後一輪都正好是那個形狀,而它一次都沒開口。**

排除的項目,逐一驗過:

* **旗標讀得到** —— 安裝版 `case-bridge/package.json` 的 `pi-harness.root` 指向本 repo,
  `pi-config/harness-config.json` 在量測期間是 `true`。
* **bridge 有載入** —— 階段閘在 run 1 擋下一次 bash,理由逐字是
  「C.A.S.E. 階段閘(CLAIM):這個佇列有 PENDING 任務,還沒有人認領」。
  **同一個 bridge 的另一個守衛在同一次 run 裡發言了。**
* **計數器認得出注入** —— 見下。

**沒有排除的:為什麼不開口。** 需要對安裝版下探針,不是繼續推理。
本 repo 自己的教訓是「探事件,不要探型別」—— 五分鐘的臨時 handler 抵過一小時的閱讀。

## 儀器本身:四種破壞、四次紅,而其中兩種是**結構性的假零**

`scripts/measure-advancer.py --self-check` 先跑,不通過就拒絕量測。

| 破壞 | 結果 |
|---|---|
| 只認 `write` 不認 `edit` | `status_writes_tool: got 1, expected 2` ✅ |
| 把 `cat status.txt` 算成寫入 | `status_writes_bash: got 2, expected 1` ✅ |
| 注入改用近似的 `customType` 字串 | `advance_injections: got 0, expected 1` ✅ |
| **不拆訊息信封** | 五個計數器同時歸零 ✅ |

前兩種是 2026-08-06 真實發生過、且會讓主指標反過來的錯誤。

### 但真正該記的是:自證第一次是**綠的,而儀器是壞的**

第一次真實 run 回報全部 0,而 session 檔有 11 KB。原因是記錄的外層信封是
`{"type": "message", "message": {...}}`,而我讀了頂層的 `role`。

**自證沒抓到,因為那份 fixture 是我憑記憶寫的。** 這正是本 repo 的疤:
**編造 payload 的 fixture 會在它所代表的東西壞掉時通過。**
fixture 已改為從真實 session `019fdebe` 抄出來的形狀。

修好之後,第二個結構性假零才浮出來:**自訂注入的記錄完全沒有 `role` 欄位** ——
它是 `{"type": "custom_message", "customType": ..., "content": ...}`。
所以兩個注入計數器在結構上**不可能**回傳 0 以外的值。

驗證方式不是再寫一個 fixture,而是**拿已保存的、已知含一次注入的真實 session 去跑**
(`docs/measurements/sessions/2026-08-06-blocked-claim-delivered.jsonl`):

```
{"tool_calls": 2, "blocked": 1, "advance_injections": 0,
 "blocked_claim_injections": 1, "status_writes_bash": 1, "assistant_turns": 4}
```

**如果沒做這一步,這份報告會寫成「推進器 0 次注入」——**
**而那個 0 是計數器產生的,不是模型產生的。**

## 順帶量到的一件事

三次 run 的模型都跑去讀 `D:/MyProject/CKs_PI_Code_Agent_Harness/`(`ls` 與 `read` README),
而它的 cwd 在 temp 目錄。**讀取不被圍堵擋,這是刻意的**,所以 Task_003 的修正沒有矛盾 ——
但它顯示訊噪比的問題在**讀取**路徑上仍然存在,只是不造成損害。

## 下一步(不在本次範圍)

1. 對安裝版 `case-bridge` 下臨時探針,量 `turn_end` 時 `spoke` / `worked` /
   `nextStep()` 三者的實際值。**不要繼續推理。**
2. 查清楚之後才有資格重測,也才有資格談預設值。

## 重現

```bash
python scripts/measure-advancer.py --self-check        # 先證明計數器會紅
# pi-config/harness-config.json: enableCaseAdvancer = true
python scripts/setup.py --mode restore
mv 02_Task_Queue <repo 之外的位置>                      # 移出,不是改名
python scripts/measure-advancer.py --runs 3 --prompt baseline --out baseline.json
# 量完:旗標設回 false、佇列移回、restore、git status 應乾淨
```
