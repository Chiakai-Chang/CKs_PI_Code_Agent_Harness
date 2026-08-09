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

