# 佇列推進器:拿掉誘餌之後的重測

**日期**: 2026-08-06
**取代**: [2026-08-06-queue-advancer-first-run.md](2026-08-06-queue-advancer-first-run.md) 的結論
(0/3),該次量測被一個**我自己製造的誘餌**汙染

---

## 為什麼重測

第一次量測得到遵循率 0/3,歸因於「模型在錯誤目錄作業」。查證後發現兩個成因必須分開:

| 成因 | 既有? | 證據 |
|---|---|---|
| 模型把相對路徑解析到 harness 根目錄 | **是** | 今天三次,其中一次在 bootstrap 之前 |
| 解析過去之後**剛好有佇列可以動手** | **否 —— 我造成的** | `00_Constitution/core.md` 由 `c6cc1ea` 加入,就在幾小時前 |

沒有第二個成因,模型解析過去會找到空的。**所以第一次的 0/3 不是推進器的成績。**

重測方式:把 harness 的 `02_Task_Queue` 暫時移開,其餘條件不變。

## 結果

```
injections: 11
sequence:  start ×3 → ESCALATION → planning → output ×2 → submit → retro ×3

distinct steps injected: 5   →   completed: 5
final state: DONE
files: action_log.jsonl · output.md · planning.md · retro.md · recipe.md · role.md · status.txt
```

| 指標 | 值 |
|---|---|
| **依不同步驟計** | **5/5 = 1.00** |
| 依每次注入計 | 5/10 = 0.50 |

**任務從 `PENDING` 一路走到 `DONE`,協定要求的檔案全部產生,`action_log.jsonl` 由 harness
自動寫出。** 這是 R1/R7/R9(先規劃、每次一件、逐項完成)第一次真的發生。

## 過程:前 16 步在錯的地方,之後自己修正了

```
 0–7   模型把所有路徑解析到 D:/MyProject/CKs_PI_Code_Agent_Harness
 7     write 進 harness 的 vendored submodule          → Directory containment 擋下
 9     改用 bash printf > 同一路徑                      → bash containment 擋下(今天才補的洞)
 1,11,15  同一步推進三次
 16    升級:同一步 3 次沒前進,請改 ESCALATED
 21    ls -la "/tmp/tmp.../02_Task_Queue/..."          ← 自己找到正確目錄
 26    printf "IN_PROGRESS" > 正確路徑                  ← 狀態第一次真的前進
 31    推進:寫 planning.md      → 照做
 39    推進:寫 output.md        → 照做
 43+   推進:寫 retro.md         → 照做
```

**兩個守衛在模型迷路時保護了 harness repo**,其中 bash 那道正是今天早上才補上的。
沒有它,模型會用 `printf >` 寫進 vendored submodule。

## 但同一份紀錄揭露一個嚴重的洞

**`status.txt` 最後是 `DONE`,而雙軌守衛沒有開火。**

原因和今天早上的圍堵守衛一模一樣:

```ts
// task-queue-guard.ts:60
const WRITE_TOOLS = new Set(["write", "edit"]);
```

模型寫狀態用的是 **bash**:

```
bash  printf "IN_PROGRESS" > .../status.txt
bash  printf "REVIEW"      > .../status.txt
bash  printf "DONE"        > .../status.txt
```

**五條 C.A.S.E. 守衛全部被繞過**,包括:

* **雙軌驗證** —— 同一個 session 設了 `IN_PROGRESS` 又設了 `DONE`,§1 明訂不可協商
* 非法轉換、一次一件、`DONE` 前 retro、任務目錄邊界

守衛沒有壞,它們只是看不到 bash。**這是今天第二次同型的洞** ——
早上是目錄圍堵,現在是 C.A.S.E. 佇列守衛。

## 結論

| 項目 | 判定 |
|---|---|
| 推進器機制 | ✅ 有效,5/5 不同步驟完成 |
| 推進器的退場預算 | ✅ 3 次 + 升級,分毫不差,而且升級之後模型自己修正了 |
| 遵循率 | **依步驟 1.00 / 依注入 0.50** |
| 魔鬼代言人的注 | 依注入計贏、依步驟計輸 —— **兩個數字都報,不合併** |
| cwd 誤判 | ⚠️ **仍然存在**,前 16 步都在錯的地方,只是這次自己修正了 |
| **C.A.S.E. 五條守衛** | ❌ **被 bash 全數繞過** |

## 下一步

1. **補 C.A.S.E. 守衛的 bash 洞** —— 優先於一切,因為現在那五條在真實使用中等於不存在。
2. cwd 誤判仍未解,但這次證明模型**可以自己修正**,所以它是效率問題不是阻斷問題。
3. 預設值仍維持 `false`,直到 bash 洞補上並重測。

## 重現

```bash
mv 02_Task_Queue 02_Task_Queue_PARKED          # 移開誘餌
# harness-config.json: enableCaseAdvancer = true;  restore
D=$(mktemp -d) && cd "$D" && git init -q
python <harness>/external/Local-Agent-Workspace/scripts/bootstrap.py .
# 建 Task_001_probe(PENDING / role.md / recipe.md)
pi --print --session-dir "$D/.sess" "這個專案是什麼?簡短說明就好。"
python <harness>/scripts/session-report.py "$D/.sess"
# 量完:旗標設回 false、把佇列移回來、restore
```

單次樣本,sampler 為伺服器啟動參數(`--temp 1.0`)。**存在性證據,不是頻率證據。**
