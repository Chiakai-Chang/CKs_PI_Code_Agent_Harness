# 結果：harness 可用性實地驗證 第一輪（2026-07-30）

協定見 [設計文件](../superpowers/specs/2026-07-30-harness-usability-validation-design.md)。
本文記錄 T1、T2 的實跑結果。**T3、T4 尚未執行。**

模型 `qwythos-27b`（lemonade gfx1151 build，`-c 262144`，切回 64/64 之後
pp 184.9 / tg 18.07 t/s）。每個任務以 `pi --print` 執行，觀察資料全部取自
`~/.pi/agent/sessions/`，未新增任何儀器。

---

## 一、觀察表

| | T1-r1 | T1-r2 | T1-r3 | T2 |
|---|---|---|---|---|
| 完成度 | **卡死** | 完成 | 完成 | 完成 |
| 回合 / 工具呼叫 | 2 / 2 | 8 / 10 | 16 / 15 | 9 / 8 |
| 工具呼叫正確性 | 全對 | 全對 | 全對 | 全對 |
| Guard 觸發 | 0 | 0 | 0 | 0 |
| Guard 誤傷 | 0 | 0 | 0 | 0 |
| 技能觸發 | 0 | 0 | 0 | 0 |
| 回報與事實相符 | — | ✓ | ✓ | ✓ |

**合計 35 次工具呼叫，全部是正確的原生呼叫**——正確的工具名、正確的絕對路徑、
參數無誤，包含一個位於本 repo 之外的暫存專案。

三次完成的結果我都獨立驗證過，不是採信 agent 的回報：
T1-r2 `Ran 21 tests OK`、T1-r3 `Ran 22 tests OK`、T2 `Ran 5 tests OK` 且 `tests/` 未被修改。

---

## 二、原始假設不成立

進這一輪之前的假設是「harness 與蒸餾其他專案過頭，導致本專案實際上沒辦法用」。

**4 個 session、35 次工具呼叫，沒有任何證據支持它。** 工具鏈、路徑處理、跨專案目錄、
參數格式全部正常；六個守衛一次都沒有干擾正常工作（誤傷 0）。

搭配前一天的量測——同樣 15,287 tokens 的注入，換模型就從 0/16 變 32/32
（[復盤 §8](2026-07-30-laguna-abandoned-and-strix-halo-survey.md)）——目前的證據方向是：
**先前「不能用」的主因是模型，不是 harness 的注入量或蒸餾程度。**

---

## 三、真正的缺口：沒有守衛看得見「靜默結束」

T1-r1 兩個回合就收工：

```
T1  stopReason=toolUse   read × 2（正確）
T2  stopReason=stop      0 呼叫   text="I've read the code. Write failing test first."
```

宣告下一步，然後結束。Pi 視為一次正常完成的回合，`--print` 正常退出，使用者拿到兩行字。

六個守衛沒有一個看得見這個形狀：

* Guard 5（repeat-call）需要重複行為才累積——這裡什麼都沒重複
* Guard 6（fabricated-work）找的是「宣稱**已完成**」——這句是「宣稱**即將做**」，語意相反
* loop guard 需要 strike 才交還——沒有任何 strike

**這是「少一個守衛」，不是「多了守衛」。** 修的方向已經存在：
`compact-continuation-bridge` 已經在用 `sendMessage(deliverAs:"followUp", triggerTurn:true)`
重新觸發一輪，缺的只是偵測「未兌現的意圖」這個形狀。

**但先別動手。** 見下一節，這次觀察被我自己的任務設計汙染了。

---

## 四、我把 T1 出壞了，三次結果全部被汙染

T1 的指派是：

> `--sources rules|neutral` 旗標沒有測試覆蓋，請用 TDD 補上：先寫會失敗的測試、確認紅燈、再讓它綠。

兩個缺陷：

1. **語意歧義**：`rules|neutral` 本意是 shell 慣例的「二選一」，但也可以讀成
   「用管線把兩組合起來」的字面語法。
2. **不可能的指令**：那個功能**已經存在**，針對它的測試必然是綠的，「先紅燈」在物理上做不到。

三次行為的差異正好對應這個歧義：

```
r1  卡死    宣告下一步就停
r2  完成    靜靜跳過紅燈要求，寫一個直接會過的測試
r3  完成    把歧義解成「新功能」，實作管線合併語法，做出真正的紅 -> 綠
```

**所以 r1 的卡死不是乾淨證據**，它可能是模型面對一個自相矛盾的任務時的反應。
本文前一節的缺口仍然真實（那個形狀確實沒有守衛看得見），但**它的發生率與觸發條件未知**。

這是本次工作階段第三次「儀器自身有缺陷」，只是換了一件外衣：
先是 fixture 大小、再是逾時被記成 error、這次是**任務指派本身自相矛盾**。
共同形狀仍然是那一句：**量測工具的缺陷會偽裝成被量測對象的性質。**

r3 的產出（管線合併語法）**已丟棄**——我只要求補測試，它擴張了範圍，
而且改變 manifest 的 `source_set` 語意，會影響既有 fixture sha 的可重建性。
規格裡「不得因為 agent 寫了就留下」那條在此生效。

---

## 五、技能零觸發：是事實，但不要過度解讀

4 個 session、35 次工具呼叫，`skill` 工具**一次都沒有被呼叫**。
每輪注入裡的 `<available_skills>` 是 42 個技能、4,681 tokens。

**但零觸發不必然是缺陷。** T2 的 bug 只有一個字元（`>` 應為 `>=`），
一個稱職的 agent 修它本來就不需要載入方法論技能；它也確實一次做對。

真正的矛盾在於 `CLAUDE.md` 自己寫著「a bug → `systematic-debugging`」，而實際沒有發生。
這是**政策與比例原則的衝突**，不是單純的機制故障。要判斷哪一邊該調整，
需要一個「複雜到真的需要方法論」的任務——目前四個任務都不夠複雜。

在那之前，不要因為這個數字去砍 `skillTiers.core`，也不要去加強觸發的措辭。

---

## 六、一個讀數上的陷阱

session 裡 assistant 訊息的 `usage.input` 是 llama.cpp 回報的**實際處理 token 數**，
不是完整 context 大小。KV prefix 命中快取時只計新 token，所以 T2 後半段出現
`in=94`、`in=101`、`in=35` 這種數字。

第一回合兩者相等（T1 首輪 `in=15,517`，與實測的每輪注入 15,287 加任務文字吻合），
後續回合會**低估**。引用這些數字時要講清楚是哪一種。

---

## 七、T3、T4：同一個形狀，在乾淨任務上重現

### T4（專案外資源盤點）

```
T1 bash  T2 bash  T3 bash  T4 read      四次呼叫全部正確
T5 stopReason=stop  calls=[]  TEXT: "Real model paths in these scripts. Check existence:"
```

指派毫無歧義，四次工具呼叫全對，然後在「該去確認檔案存不存在」那一步宣告意圖、結束回合。
8 分 49 秒，零產出。**§三那個缺口在乾淨任務上重現了**，§四的保留可以撤銷。

### T3（網頁研究）：三個缺陷疊在一起

session 只有 2 回合、1 次工具呼叫（`deep_research`），那一次跑了 **44 分鐘**。
`deep_research` 拆成 4 個子問題、各開一個 agent process，回傳的四個「答案」是：

```
1. "No results. Fetch GitHub issues directly."
2. "All tests pass. Now collect more info about the draft mechanism itself to answer the sub-question properly."
3. "Continuing to read the article:"
4. "(failed after 900s — child agent exited null with no answer. [ecc-bridge] ECC Submodule Version: 2.0.0)"
```

前三個都不是答案，是**子代理宣告下一步之後就結束回合的殘句**——同一個形狀，一次三例。

疊了三個獨立缺陷：

1. 子代理在步驟交界靜默結束（×3）
2. **`deep-research-bridge` 不驗證回傳是不是答案**，把最後一則訊息原樣收下
3. **子行程的啟動橫幅污染答案**：`[ecc-bridge] ECC Submodule Version: 2.0.0` 出現在答案文字裡

同時有一個**明確的 harness 勝利**：bridge 的綜整指示要求「若子問題失敗就說它未解決，不要用記憶填補」，
主模型確實照做，誠實回報查不到，沒有捏造出處。

---

## 八、第一輪收斂（6 個 session）

```
40 次工具呼叫      全部正確
0  次守衛觸發      因此誤傷也是 0
0  次技能觸發
3 / 6 個任務產不出可用結果，全部經由同一個機制
靜默結束共 5 次    T1-r1、T3 子代理 ×3、T4
```

### 依嚴重度排序的缺陷清單

| | 缺陷 | 觀察 | 狀態 | 說明 |
|---|---|---|---|---|
| **P0** | 步驟交界靜默結束 | 5 次，造成 3/6 失敗 | **已修，真實驗證** | Guard 7。`stopReason=stop`、零呼叫、文字宣告即將做的下一步 |
| **P1** | deep-research 收下非答案 | 1 任務／3 子問題 | **未驗證** | 推測 P0 修好會改善——**這是推測，沒重測** |
| **P2** | 子行程橫幅污染答案 | 1 | 未修 | stdout 未與答案分離 |
| **P3** | 多代理成本模型不匹配本機 | 1 | 未修 | 44 分鐘零產出。取捨題不是 bug |
| **P4** | PowerShell `$` 被 bash 吃掉 | 3 回合 | **已修，真實驗證** | Guard 8。擋在 `tool_call`，每輪零 token |
| **P5** | 子代理無監督寫入原始碼 | 2 筆寫入 | **已修，真實驗證** | `--exclude-tools bash,edit,write` |
| **P6** | 提前收斂：完成但答案錯 | 1 | **已知，暫不修** | 守衛無法判斷 glob 是否涵蓋任務語意。見 §十二 |
| — | 技能 0/6 觸發 | 6 | 未判定 | **尚不算缺陷**：六個任務都不夠複雜。在有反證前不要動 `skillTiers` |

守衛累計：**觸發 2 次、誤傷 0 次**。

**P3 是「蒸餾過頭」的精確形式**：不是 token 太多（那個假設已被模型對照推翻），
而是**從雲端規模專案蒸餾來的能力，其成本假設在 18 t/s 的本機 serving 上不成立**。

### 沒有出現的

工具呼叫錯誤、守衛誤傷、捏造。這三項的缺席，加上 40/40 的呼叫正確率，
是「harness 本身沒有把 agent 搞壞」最直接的證據。

---

## 九、P0 已修並在真實 session 驗證

Guard 7（`announcesUnfulfilledNextStep`）。先寫測試確認全紅（3 個正向失敗、6 個負向對照通過），再實作。

偵測**只看訊息結尾**：結尾是冒號，或最後一句以意圖動詞開頭。看整段會誤傷 T2 那句正確結案
（中間有「The issue: ... used strict `>`」的前瞻語氣，但結束在「Changed to >=.」）。
兩條否決：結尾是問句、或含「如果你願意」→ 不觸發（把決定交還使用者是正確終止狀態）；
給使用者的建議不算宣告（T3 那份誠實失敗報告列了下一步，但那是建議）。
糾正訊息**不回引卡住的原文**——2026-07-28 那次 transformer 就是這樣餵出死結。上限 2 次。

真實 session 驗證（同一份在 T4 卡死的指派）：

```
[6] assistant       "Real model paths in these scripts. Check existence:"
[7] custom_message  customType="loop-guard"    <- Guard 7 觸發
[8] assistant       toolCall                   <- 模型繼續工作，跑到第 7 回合
```

觸發 1 次、誤傷 0 次。421 tests OK。

**說法要收窄**：這是 n=1，而且那個任務**仍然沒完成**（卡在下一節的 P4）。
正確的陳述是「它打斷了卡死」，不是「它讓任務成功」。

---

## 十、P4、P5：兩個新缺陷，其中一個比 P0 更嚴重

### P4 — Windows 跨 shell 的引號與變數插值

Guard 7 把 T4 拉回來之後，session 卡在另一個地方：模型透過 `bash` 工具下
`powershell -Command "& { $bats = Get-ChildItem ... }"`，**`$` 變數在傳進 PowerShell 之前
就被 shell 吃掉**，連續三次 `bash` 回傳錯誤：

```
foreach 後面應該是變數名稱          $bats / $results 消失
/usr/bin/bash.FullName ObjectNotFound
```

`CLAUDE.md` 寫著「Pi 在 Windows 上也用 bash 執行」，但沒有任何東西告訴模型
「所以不要在 bash 裡寫帶 `$` 的 PowerShell 單行指令」。

### P5 — deep-research 子代理無監督寫入原始碼（嚴重度高於 P0）

T3 是一個**純研究問題**，主 session 只有一次工具呼叫（`deep_research`）。
但在它的時間窗內：

```
00:51:22  scripts/make-probe-fixture.py  被修改（實作了與研究無關的管線合併功能）
01:13:04  qwen35_mtp_findings.md         被建立在 repo 根目錄
```

程式碼確認（`pi-extensions/deep-research-bridge/index.ts`）：

```ts
const inv = piInvocation(["--print","--mode","json","--no-session",
                          "--append-system-prompt", promptFile, childPrompt(subQuestion)]);
const proc = spawn(inv.command, inv.args, { cwd, ... });   // cwd = 母 session 的 cwd
```

三件事疊起來：**子代理的 cwd 就是 repo**、**沒有任何工具限制**（拿到完整的
`write`/`edit`/`bash`）、**`--no-session` 讓稽核軌跡從設計上不存在**。

那句莫名的子代理回傳「All tests pass. Now collect more info about the draft mechanism itself」
因此說得通——那個子代理根本不在研究，它在跑測試改程式。

bridge 作者**想過**失控問題：`CHILD_MARKER` 環境變數防止子代理遞迴呼叫 `deep_research`，
註解寫著「Without it, one confused decomposition could fork agents until the machine dies」。
**想到了遞迴，沒想到寫入權。**

**為什麼比 P0 嚴重**：P0 是「事情沒做完」，看得見；P5 是「做了你沒要求的事，而且看不見」。
若不是為了 commit 順手跑了 `git status`，那個改動會靜默留在工作區被下一次 commit 帶走。

**這是「蒸餾過頭」的第二個精確形式**：多代理能力接進來時**沒有帶權限邊界**。

---

## 十一、我自己這一輪的四個錯誤

1. **我在 P0 的 commit 之後回報「(clean)」，但工作區並不乾淨**——那是無條件 `echo`，
   斷言了指令沒有驗證的狀態。與「儀器把失敗變成缺席」同一家族，只是這次犯在回報上。
2. **T3 沒落實我自己訂的停止規則**，跑了 44 分鐘。T4 改用 `timeout 900` 才受控。
   **靠人盯的規則不是規則。**
3. **T1 指派出壞了**（見 §四）。
4. **P5 差點整個漏掉。** 只因為要 commit 才順手跑 `git status`。
   **觀察表只記錄了 agent 說了什麼、呼叫了什麼，沒有記錄它改變了什麼**——
   而漏掉的正是這一輪最嚴重的缺陷。

第 4 點已回寫進協定：每個 session 結束必須檢查 `git status` 與工作區異動。

---

## 十二、P4 已修並驗證，但同一輪露出 P6

Guard 8（`crossShellQuotingGuard`）：只擋**雙引號內未轉義的 `$`**。單引號與 `\$` 放行——
那是正確寫法，擋掉正確寫法比原本的 bug 更糟。四組負向對照鎖住，含最寬的
「一般 bash 用 `$`」。擋在 `tool_call`，每輪零 token 成本。

真實 session 驗證（同一份先前逾時的 T4）：

```
T4  bash: powershell -Command "$paths=@('C:\models\...
    ERROR: 這個指令會先經過 bash…3. 直接用 bash 原生指令（ls / find / grep）完成同一件事
T5  bash: for f in "C:/models/llama-bin-win-hip-radeon-x64/llama-se…   <- 採納第 3 個建議
T6  完成
```

12 分鐘完成，前一次是 20 分鐘逾時。Guard 7 本輪 0 次觸發（沒有卡死，也就不該觸發），零誤傷。

### P6 — 提前收斂：任務完成、格式漂亮、答案錯誤

同一個 session 的產出是一份工整的表，開頭寫「已盤點完畢」、「共有兩個啟動腳本」。
獨立盤點的真實答案是 **10 個腳本、11 個缺失目標**，它漏了 8 個
（`APEX-Laguna_hip`、`FableFusion-711_HIP` ×2、`Hy3_HIP` ×3、`nemotron`、`Opus-Distill-27B` ×3）。

原因在第一步：

```
T1  bash: ls -R C:/models/run-*.bat C:/models/launch-*.bat
```

它只 glob `run-*` 與 `launch-*`，所以從頭到尾只看見 19 個腳本中的 2 個。
它找到的那兩個是對的，沒有捏造任何東西——**搜尋範圍比任務範圍窄，而它沒有檢查這件事**。

這是新的一類：不是卡死（完成了）、不是捏造（沒發明檔案）、不是誤傷。
**而且它大概不是守衛能修的**——守衛無法判斷一個 glob 是否涵蓋了任務的語意範圍。
可行的方向是注入規則層面的「宣告清單完整之前，先列出完整候選集」，
但那要花每輪 token，且與 `CLAUDE.md` 既有的證據紀律重疊，值不值得要另外評估。

**對協定的影響比對程式碼的影響大**：觀察表的「完成度」欄位不足以判斷成敗。
`完成 ≠ 正確`。本輪之所以抓到，只因為我**自己動手重做了一次盤點**——
而我自己前兩次驗證也都寫錯（sed 壞掉、regex 漏掉 `set "MODEL_PATH="` 的寫法），
第三次才對。任務本身就容易錯，正因如此，一份自信的錯誤摘要比一次卡死更危險。

協定新增一欄：**答案正確性（由人獨立重做，不採信 agent 的回報）**。

---

## 十三、待辦

* **P0 已排定修復**（先寫失敗測試與負向對照）。
* T1 若要重跑，**必須先改掉指派文字**：拿掉歧義、拿掉不可能的紅燈要求。
* 停止規則要用機制而不是靠人盯：T3 因為我沒盯而跑了 44 分鐘，T4 改用 `timeout 900` 才受控。
