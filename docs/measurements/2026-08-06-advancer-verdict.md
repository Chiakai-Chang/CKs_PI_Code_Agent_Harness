# 佇列推進器:三個 bash 洞補完後的重測與判定

**日期**: 2026-08-06
**任務**: `Task_008_advancer_verdict`
**前一次**: [2026-08-06-advancer-clean-rerun.md](2026-08-06-advancer-clean-rerun.md)(5/5 步驟,終態 DONE)

## 環境(基準線沒記,這次補上)

| 項目 | 值 | 來源 |
|---|---|---|
| 模型 | `GRM-3.2-Sky-ONYX-balanced.gguf` | session JSONL 的 `message.model` 欄位 |
| `n_ctx` | 262144 | `/props` |
| sampler | `temperature 1.0 / top_p 0.95 / top_k 20 / min_p 0.0` | `/props` |
| 旗標 | `enableCaseAdvancer: true`(量完已改回 `false`) | |

**基準線與本次是同一個模型**,由 session 欄位證實,不是假設。

## 先說再量:賭注與結果

| 賭注(寫在 run 之前) | 結果 |
|---|---|
| 一、模型會撞滿三次讓守衛退場,然後照樣用 bash | ❌ **全錯。5 次 run、21 次狀態寫入,`bash` 寫入 status.txt = 0** |
| 二、遵循率不會明顯下降 | ❌ **錯。5 次 run 沒有一次走到 DONE** |
| 三、`uncheckedWrites` > 0 | 無法計:該數字只送到 TUI,`--print` 看不到 |

**三個賭注錯兩個、一個問錯問題。** 記在這裡是因為賭注的用途就是這個。

## 結果

| run | 提示 | 工具呼叫 | 擋阻 | 推進注入 | 升級 | status 寫入(write/edit) | status 寫入(bash) | blocked-claim | 終態 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 基準線 | 53 | 4 | 13 | 3 | **4** | **0** | 1 | ESCALATED |
| 2 | 基準線 | 50 | 1 | 20 | 5 | **13** | **0** | 0 | ESCALATED |
| 3 | 基準線 | 21 | 11 | 9 | 1 | 0 | 0 | 0 | **PENDING**(全程卡住) |
| 3b | 基準線(無誘餌) | 38 | 2 | 13 | 3 | **4** | **0** | 1 | ESCALATED |
| 4 | **研究型** | 93 | 72 | 42 | 1 | 0 | 0 | 7 | **PENDING**(我中止) |

基準線那次:3 次狀態寫入**全部是 `bash printf >`**,五條 C.A.S.E. 守衛一次都沒有機會發言。

## 一、Task_004/005 的修正成立

**21 次成功的 status.txt 寫入,全部走 `write`/`edit`,`bash` 0 次。**
不是因為模型變乖 —— run 1 有 `bash printf > status.txt` 被 tool-first 守衛擋下的紀錄,
擋下之後它改用 `write`。**這正是那條守衛存在的目的,而它現在真的在流程裡發生。**

`blocked-claim` 在 3/5 次 run 裡響了(共 9 次),那是同一天稍早才第一次接通的守衛。

## 二、但沒有一次走到 DONE,而原因不是模型

推進器的退場門檻 `MAX_ADVANCES_PER_STEP = 3` **數的是注入次數,不是停滯次數**。
它在每個 `turn_end` 注入一次;而模型完成一個步驟(讀檔、思考、寫檔)本來就要好幾輪。
所以一個**正在正常進行**的步驟,到第四輪就會被判定「停了 3 次都沒有前進」。

確定性重現(不經模型,直接驅動 `advance()`):

```
1 PENDING      -> 下一步:改 IN_PROGRESS
2 IN_PROGRESS  -> 下一步:寫 planning.md
3 +planning    -> 下一步:寫 output.md
4 +output      -> 下一步:改 REVIEW 送審
5 REVIEW       -> 下一步:寫 retro.md
6 +retro       -> 已在 REVIEW,核可要另一個 session
7 same again   -> 同上
8 same again   -> 同上
9 same again   -> ESCALATE      ← 終點步驟被判定為卡住
```

**狀態表本身是對的**(六個狀態全部推對,含 `IN_PROGRESS\n` 這種帶換行的值)。
壞的是退場計數器,而且它有兩種壞法:

1. **正常進行中的步驟被當成停滯** —— 因為單位是「注入次數」不是「有沒有進展」。
2. **終點步驟必然升級** —— 「交給另一個 session 核可」是一個**設計上不會再變的狀態**,
   計數器卻要求它繼續變,三次之後宣告卡住。run 2 逐字重現了這一段。

**修法方向明確:**只有在「上次注入之後任務包沒有任何變化」時才累加計數器。

## 三、真正的阻斷者是 cwd 混淆,不是推進器

| run | 擋阻 | 內容 |
|---|---|---|
| 3 | 11 | 全部是模型嘗試寫進 **harness repo** 的路徑,被 containment 擋下;9 次之後放棄,終態仍 PENDING |
| 4 | 72 | 同上,目標包括 harness 的 vendored submodule `external/Local-Agent-Workspace/C.A.S.E._Framework/02_Task_Queue/` |

run 3 咬的是 `02_Task_Queue_PARKED` —— **那是我為了量測而改名的誘餌**,是我製造的。
所以 run 3 重跑成 run 3b(把佇列整個移出 repo),而 run 3 的數字照列不刪:
它同時也是 containment 守衛連續擋下 11 次、一次都沒漏的紀錄。

**但 run 4 沒有誘餌,照樣發生。** 這一項(`Task_003_cwd_confusion`)先前被降級為
「效率問題,模型會自己修正」。**本次量測推翻那個降級:2/5 次 run 被它整場吃掉。**

## 四、研究型 run 直接回答了擁有者的抱怨

擁有者的原話:「還是會直接開始搜尋網頁,然後煞有其事的搜尋可能十幾次,然後給我一個結論」。

run 4 的前 11 個動作,逐字:

```
web_search web_search web_open web_open web_open web_search bash web_search read write write
                                                                          ↑ 第一次推進注入在這之後
```

**推進器一次都沒能阻止「先搜再說」** —— 因為它在 `turn_end` 才說話,
而模型的第一輪裡就已經搜完六次了。

**這不是推進器做錯,是它的位置決定了它做不到。** 要在動作之前介入,
唯一到得了的通道是 `tool_call` 的擋阻(引用閘、深度閘就在那裡),不是 `turn_end` 的建議。

## 判定

**`enableCaseAdvancer` 維持 `false`。**

不是因為它沒用 —— 它確實把任務從 PENDING 推過 planning / output / submit / retro,
在 3/5 次 run 裡產生了完整的任務包檔案。而是因為:

1. **它現在保證會升級。** 退場計數器數錯單位,終點步驟必然被判卡住。先修這個,再談預設。
2. **它的位置決定它管不到擁有者真正抱怨的事。** 先搜再說發生在第一輪之內。
3. **更上游的阻斷者沒解決。** cwd 混淆吃掉 2/5 次 run,`Task_003` 的降級必須撤銷。

## 下一步(依序)

1. `Task_003_cwd_confusion` **升回最高優先** —— 它是目前最大的單一失敗來源。
2. 修退場計數器:改為「任務包自上次注入後無變化」才累加,終點步驟不累加。
3. 修完再重測,並且**測研究型提示**,因為那才是擁有者的場景。

## 重現

```bash
# harness 端
#   pi-config/harness-config.json: enableCaseAdvancer = true; python scripts/setup.py --mode restore
#   把 02_Task_Queue 移出 repo(不是改名 —— 改名留下的目錄仍然會被模型當成佇列)
D=<各自獨立的 temp 目錄> && cd "$D" && git init -q
python <harness>/external/Local-Agent-Workspace/scripts/bootstrap.py .
# 建 Task_001_probe(PENDING / role.md / recipe.md)
pi --print --session-dir "$D/.sess" "這個專案是什麼?簡短說明就好。"
# 量完:旗標設回 false、佇列移回、restore、git status 應乾淨
```

計數依 `message.role` / `toolName` / `customType` 過濾,不做子字串比對。
`edit` 也算 status 寫入 —— 第一版漏了它,run 2 因此回報 0,差一點就讀成「守衛被繞過」。
