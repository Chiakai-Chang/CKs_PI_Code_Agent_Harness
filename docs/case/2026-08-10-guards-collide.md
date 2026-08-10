# 四個守衛同時開口,而唯一有用的那一句只講了一次

**日期:2026-08-10**
**起因:** 為了驗證任務小憲法注入(Task_023),跑了一個真實 C.A.S.E. 專案的 run。
**結果:注入 0 次 —— 因為任務從頭到尾沒有被認領。** 而查下去發現的不是新功能的問題。

---

## 1. 這個 run 發生了什麼

Session `019fe880`,33 次工具呼叫,`status.txt` 最後仍是 `PENDING`,`output.md` 不存在。

**模型從第一次呼叫就跑到錯的目錄** ——
用 `D:/MyProject/CKs_PI_Code_Agent_Harness/02_Task_Queue/`,
而它的 cwd 是 `.../scratchpad/tc-live`。

這是已記錄的 cwd 混淆疤:Pi 的系統提示裡 harness 安裝路徑以技能 `<location>` 出現 28 次,
cwd 只出現一次。`harness-root.ts` 就是為此存在的。

## 2. 拒絕的分布 —— 問題在這裡

```
refusals by guard:
  phase gate     9
  ECC gate       1
  containment    1
  tool-first     1

sequence:
  ECC | phase | phase | phase | containment | phase | phase | tool-first |
  plain | phase | plain | phase | plain | phase | plain | phase
```

**唯一診斷出真正病因的那一則,只出現一次。** 就是 containment 那一則,
而且它給的資訊完全正確,連改好的路徑都附上了:

> 你要寫的路徑在 **harness 的安裝位置**(D:/MyProject/CKs_PI_Code_Agent_Harness),
> 不是你這次的工作目錄(...tc-live)。會這樣不奇怪 —— 系統提示裡每個技能的
> `<location>` 都指向那裡,而工作目錄只出現一次。……
> 路徑是:`.../tc-live/02_Task_Queue/Task_001_Inventory/status.txt`

**1 次 vs 9 次。** 模型收到的主要訊號是階段閘,而階段閘講的是別的事。

## 3. 階段閘的三個實際缺陷

逐字取出九則階段閘訊息後:

### (a) 它說了一句假話

第二則寫著:

> C.A.S.E. 階段閘(CLAIM,第二次):換個做法 …… **下一次我不會再擋。**

**然後它又擋了七次。**

本 repo 花了整週在講「模型會把 N 次拒絕、零次許可,理性地推廣成『這件事不被允許』」。
**一個說話不算話的守衛,比一個沉默的守衛更糟** —— 它在訓練模型忽略守衛說的每一句話。

### (b) 階梯用完就原地打轉

第 3 到第 8 則**逐字完全相同**,連續六次。梯子只有三階,之後就重複最後一階。

### (c) 它一直叫模型做它正在做的事

第三則說:

> 具體到可以照做 —— `write` 到 `02_Task_Queue/<任務資料夾>/status.txt`,
> 內容就是 `IN_PROGRESS` 六個字

**模型正在做這件事。** 它寫的就是 `.../02_Task_Queue/Task_001_Inventory/status.txt`,
內容就是 `IN_PROGRESS`。失敗的原因是**根目錄**,而階段閘對根目錄一無所知,
還一直重複那句已經被照做的指示。

## 4. 這件事的形狀

守衛各自都是對的。**合起來產生的訊號是「什麼都不准」,而不是「你的目錄錯了」。**

本 repo 已經有一條記錄在案的教訓:
「拿掉一個選項的守衛,必須配一個在選項回來時開口的東西」(`phase-notice.ts` 就是為此而生)。
今天這個是它的鄰居:

> **多個守衛同時擋同一次呼叫時,說話的順序決定模型學到什麼。
> 而目前沒有任何東西決定順序 —— 誰先註冊誰先擋。**

一個 tool_call 只會有一個守衛擋成功(擋下後其餘 handler 被跳過,已於 2026-08-06 實測)。
所以**「哪一個守衛先開口」不是排版問題,是唯一被聽見的那句話是什麼的問題。**

## 5. 待修(尚未動工,依便宜程度排序)

1. **刪掉那句假話。** 「下一次我不會再擋」除非真的是最後一次,否則不能出現。
   這是一行字的修改,而它現在正在教模型不要相信守衛。
2. **階梯用完不要重複同一句。** 六次逐字相同等於六次沒說話。
3. **同一次呼叫有多個守衛可擋時,優先讓能診斷根因的那個說話。**
   containment 知道「你在錯的磁碟」,階段閘只知道「還沒認領」——
   前者是後者失敗的原因,順序應該反過來。

## 6. 對 Task_023 的意義

**任務小憲法注入這次完全沒有被執行到**,因為它掛在「認領成功」這一刻,而認領從未成功。

這是 `a-guard-that-never-fired-is-unvalidated` 的第二次:
單元測試 29 條綠、七個蓄意破壞全紅、變異掃描 0 存活者、安裝版一致 ——
**而真實 run 觸發次數為 0**。差別是這次病因當場診斷得出來,而且不在新功能身上。

重跑時把 cwd 在提示裡講死,先讓認領成功,才能驗證注入。

---

# 追查之後:9 次階段閘拒絕裡,大部分根本是誤擋

回頭看第一個 run 的觸發點,差別不在指令做什麼,而在有沒有 `2>/dev/null`:

```
1  ls "D:/..."                                → ECC gate
2  ls "D:/.../02_Task_Queue/" 2>/dev/null …   → 階段閘
3  find "D:/..." -type f -o -type d 2>/dev/null → 階段閘
4  ls -la "D:/..."                            → 沒有被擋
```

實測抽取器:

```
"ls 02_Task_Queue/ 2>/dev/null"  ->  ["/dev/null"]
"ls -la 02_Task_Queue/"          ->  []
```

**`2>/dev/null` 被抽成寫入目標 `/dev/null`。** 它不是 `status.txt`,
於是 CLAIM 階段判定「你在寫非狀態檔」並拒絕。

`bash-containment.ts` 從一開始就有 `isScratch`;
`case-bridge/task-queue-guard.ts` 的抽取器(階段閘、佇列守衛、認領偵測共用)沒有。
**同一個疏漏,兩個地方,只有一個被補過。**

## 順著查下去,containment 有同一個疏漏的鏡像 —— 而且更嚴重

兩個抽取器都先收集重導向,然後**把重導向的 token 留在運算元裡**。實測:

```
cp secret.txt D:/elsewhere/out.txt              -> BLOCKED
cp secret.txt D:/elsewhere/out.txt 2>/dev/null  -> *** ALLOWED ***
mv a.txt D:/elsewhere/b.txt 2>/dev/null         -> *** ALLOWED ***
```

`cp` 的目的地取「最後一個運算元」,而最後一個運算元變成了 `2>/dev/null`,
**真正的目的地從此沒有被看過**。

**在 `cp`/`mv` 後面加 `2>/dev/null`,就能把檔案複製到專案外而不被目錄圍堵發現。**
而 `2>/dev/null` 是日常慣用寫法 —— 這條路踩得到,不必刻意。

## 一個疏漏,兩個方向相反的後果

| | 階段閘 | 目錄圍堵 |
|---|---|---|
| 症狀 | **誤擋**無害的 `ls … 2>/dev/null` | **漏放**逃出專案的 `cp … 2>/dev/null` |
| 後果 | 9 次拒絕淹掉唯一有用的那一則 | 圍堵守衛的核心職責被繞過 |

## 已修

兩個抽取器都加上 `stripRedirections()`(處理黏在一起的 `2>/dev/null` 與分開的 `> out.txt`),
並在抽取層丟棄 `/dev/` 目標。兩者現在對所有測試輸入**逐字相同**。

證據(全部寫這段時實跑):

* 逃逸已封:`cp s.txt D:/elsewhere/o.txt 2>/dev/null` → BLOCKED
* 沒有誤擋:專案內的 `cp a.txt sub/b.txt 2>/dev/null` → 允許;`echo x > /tmp/t.log` → 允許
* 三個蓄意破壞全部變紅
* `python -m unittest discover -s tests` → **Ran 1177 tests, OK**
* `verify-bridges.py` → 13 bridges,0 failures

## 剩下沒動的

第 2 項(階梯用完重複同一句)與第 3 項(誰先開口的順序)仍未處理。
但**這次的修正把第 3 項的急迫性降低了不少** —— 9 次階段閘拒絕裡,
大部分本來就不該發生。順序問題還在,只是規模小得多。

**教訓:守衛互撞看起來像優先權問題,查下去是一個抽取器的錯。
先問「這些拒絕本來就該發生嗎」,再問「誰該先講話」。**

---

# 第 2 項已修:階梯不再重複,改成把閘門看得到的東西拿出來

## 重複是怎麼來的

八回合預算、四階梯子,索引邏輯讓 turns 3–7 全部落在第 2 階:

```
turn 1: rung 0   turn 5: rung 2
turn 2: rung 1   turn 6: rung 2
turn 3: rung 2   turn 7: rung 2
turn 4: rung 2   turn 8: rung 3
```

**五次逐字相同。**

## 修法不是再多寫幾段話

補幾段文字是最順手的修法,而它是錯的。**那個 run 缺的不是措辭,是資料** ——
模型在猜路徑,而階段閘手上就有佇列目錄、可以直接列出來,卻一直背誦
`02_Task_Queue/<任務資料夾>/status.txt` 這種**路徑的形狀**,好像形狀才是問題。

第 2 階現在印出它看得到的東西:

```
C.A.S.E. 階段閘(CLAIM,第 3 次,共 8 次):不再重複同一句話,直接給你我看得到的東西。
我讀的佇列是:C:/…/scratchpad/tc-live/02_Task_Queue
裡面等待認領的任務,以及要寫的檔案:
  - Task_001_Inventory  ->  C:/…/tc-live/02_Task_Queue/Task_001_Inventory/status.txt
如果你剛才寫的路徑不在上面這份清單裡,那就是路徑錯了 —— 上面那些是絕對路徑,直接用。
```

**這正好回答第一個 run 的失敗**:模型寫的路徑在另一顆磁碟上,而它從來沒被告知
「我看到的佇列在這裡」。清單上限 5 筆,超過會說「另外還有 N 個」——
**靜靜截斷的清單會被讀成完整清單**,而「我的任務不在上面」是模型會照著行動的錯誤結論。

## 測試改成行為測試,不是字串比對

先前那批測試比對原始碼裡的常數名稱,而第 2 階變成函式之後全部壞掉 ——
**測試綁在實作的拼法上,而不是它的行為上**。改成跑完整條 8 回合階梯再斷言:

* 只有真正最後一則自稱最後
* **沒有任何一則與前一則相同**
* 中段那幾則含真實任務名與 `status.txt` 絕對路徑
* 第一則不含清單(開場就是一牆路徑會蓋掉唯一那句解釋)

四個蓄意破壞全部變紅。

## 變異掃描順帶挖出模組自己沒兌現的承諾

`phase-gate.ts` 開頭寫著 **"Fails open on anything it does not recognise"** ——
而**沒有任何測試驗過這句話**。掃描報出的六個存活者裡,逐一手動跑過之後:

* 一個是我這次新增的(清單上限 5),補測試殺掉
* 一個是**真的看得到差別,而且正是今天的情境**:交付物寫到錯誤根目錄時,
  靠「用資料夾名稱認任務」那半邊才認得出來 —— 補了測試
* 四個確認等價(下游 fail-open 兜住),寫進 allowlist 並附上實測論證

**「fails open」從宣稱變成了四條測試。**

## 現況

* 第 1 項(假承諾)—— 已修
* 第 2 項(階梯重複)—— 已修
* 第 3 項(誰先開口)—— 仍未動,但急迫性已大幅下降:
  那 9 次階段閘拒絕裡大部分是 `2>/dev/null` 造成的誤擋,已經不會再發生

證據(寫這段時實跑):`Ran 1184 tests, OK`;`verify-bridges.py` 13 bridges 0 failures;
`check-guard-mutations.py --only phase-gate --all` 4 survivors,全部有論證。

---

# 第 3 項已修:階段閘在別人有更好的抱怨時讓位

## 觸發它的真實 run

Session `019fe912`,提示是刻意含糊的「請幫我盤點**這個專案**的 src/ 模組並產出報告」——
不指名任務、不指名 cwd。

模型把「這個專案」解讀成 **harness 安裝目錄**,在裡面工作了 25 次呼叫
(讀 `pi-skills/`、`pi-extensions/`),然後三次嘗試寫入
`D:/MyProject/CKs_PI_Code_Agent_Harness/wiki/`。

```
tool calls: 25   errored results: 5
phase-gate refusals: 3   distinct texts: 2
TASK-CONSTITUTION BLOCKS: 0
status.txt: PENDING      output.md: MISSING
```

**repo 沒有被污染 —— 但擋下來的是階段閘,不是目錄圍堵。**
五個錯誤裡:兩個 ENOENT,三個階段閘。**containment 一次都沒有開口。**

## 為什麼這是最糟的一種擋法

一個 `tool_call` 只有一個守衛擋得成,**先開口的就是唯一被聽見的**。

階段閘說的是「**先去認領任務**」—— 這句話**是真的**,而且是錯的那一句。
containment 知道的是「你在另一個專案裡,正確路徑是這個」,而它被跳過了。

**模型照著它收到的那句話做,在錯的專案裡,直到跑完。**

## 修法:局部讓位,不動載入順序

```ts
if (allWritesEscapeProject(queueDir, writes)) return null;
```

**當這次呼叫的每一個寫入目標都落在它守護的專案之外,階段閘不擋。**
不改 bridge 載入順序 —— 那是全域且脆弱的。

**讓位沒有放行任何東西:** containment 拒絕的正好就是這裡不再拒絕的那些呼叫。實測:

```
write D:/some/other/checkout/wiki/module-index.md   -> escapes cwd: true
write D:/some/other/.../Task_001_probe/output.md    -> escapes cwd: true
bash  mkdir -p /d/other/wiki && echo x > …/a.md     -> BLOCKED
harness-root 重導提示仍然提供正確路徑            -> true
```

範圍很窄:**只要有一個目標在專案內就照擋**(`every`,不是 `some`),
研究工具不受影響(它們沒有寫入目標)。四個蓄意破壞全部變紅。

## 推翻了昨天自己寫的一條測試

`test_a_deliverable_written_to_the_wrong_root_is_still_recognised`
是 2026-08-10 早些時候寫的,依據是一個變異存活者,斷言**錯誤根目錄的交付物仍要被階段閘認出並拒絕**。

**今天的 run 證明那正好相反** —— 階段閘擋下那些呼叫,正是 containment 從未開口的原因。

已換成 `test_a_task_named_by_a_relative_path_is_recognised`:
`taskOf` 用資料夾名稱比對的那一半仍然需要,而它真正的用途是**相對路徑**
(相對路徑與佇列沒有共同的絕對前綴)。舊測試的理由被逐字引用在新測試的 docstring 裡。

## 順帶發現:allowlist 條目會過期

變異掃描報出 `phase-gate.ts:330:38`,而那**就是先前已列入 allowlist 的 `287:38`** ——
我在上面插了程式碼,行號位移,**條目就靜默失配,存活者看起來像新的**。

危險在於:下一個人可能會重新論證它,或者更糟 —— 去「修」一段其實不可達的程式碼。
已在 allowlist 的 `_comment` 裡寫明這個性質。

## 三項全部完成

| | 狀態 |
|---|---|
| 1. 假承諾「下一次我不會再擋」 | ✅ |
| 2. 階梯逐字重複五次 | ✅ |
| 3. 誰先開口 | ✅(局部讓位) |

## 仍未驗證的

**新的第 2 階(帶佇列資料那一則)在真實 run 裡從未觸發過** ——
`019fe912` 只累積 3 次拒絕,而它要第 3 次以上才出現。
諷刺的是那一階會印出「我讀的佇列是:`…/gate-live/02_Task_Queue`」,
**正好會戳破那個 run 的誤解**。

證據(寫這段時實跑):`Ran 1192 tests, OK`;`verify-bridges.py` 13 bridges 0 failures;
`check-guard-mutations.py --only phase-gate --all` 7 survivors,全部有論證。

