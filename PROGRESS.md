# 總控:進度、收穫、脈絡

> **這份文件的用途:** 每次工作結束後在這裡留一筆 —— 做了什麼、學到什麼、詳細文件在哪。
> 它是唯一需要從頭讀的檔案;其餘文件都從這裡連出去。
>
> **它被檢查所守著:** `tests/test_progress_ledger.py` 要求 `docs/case/` 與
> `docs/measurements/` 底下每一份文件都被本檔連到。沒人讀的紀錄是這個 repo 反覆踩到的坑
> (`global_dod.md` 曾經是一份沒人讀的未填範本),所以這份索引由測試維持,不靠記得。

---

## 現在在做什麼

**上一段工作(2026-08-09 ~ 08-10):反漂移與守衛品質。**
起因是擁有者的問題:「跑到第 18 步還記得我原本要完成什麼?」

**當前認領中:** T-A7(`cd 出去 && 執行` 的圍堵破口)。T-A1/A2/A3/A6 已由擁有者在對話中口頭核可(Path A)。

> **2026-08-11 重排。** [Round 14](docs/mece/rounds/2026-08-11_round14_回到起點與外部實證.md)
> 用外部實證與擁有者的真實 session 重查整條線,結論是**先前的排序建立在一個探針假象上**:
> 探針的 cwd 自己叫 `D--MyProject-CKs-PI-Code-Agent-Harness`,而真實 session 的對照是
> **228 次呼叫碰到 harness 路徑 1 次**。**T2 撤銷、技能遷移擱置(附觸發條件)。**

---

## 宏觀目標與微觀目標的對齊

**宏觀(擁有者原話):**
> 「每次專注做一件事,做完復盤,有發現就增加 task queue」
> 「他多搜幾次是好的阿?越多越好不是?**我抱怨的是他沒有先規劃就開始**」

拆成三個可判定的層次:

| 層 | 目標 | 現況(2026-08-11 PiTaskLab 六個 run) |
|---|---|---|
| **L1 對齊** | Pi 在**正確的專案**裡工作 | ✅ 6/6 都在 PiTaskLab 內,無一次碰到 harness 路徑 |
| **L2 流程** | 先認領 → 先規劃 → 才產出 → 有驗收物才進 REVIEW | ✅ 5/6 完整走完(11/11);失敗的 run 3 已定位到兩個缺陷並修好 |
| **L3 續航** | 長 cycle 裡不漂移 | ⚠️ 未測 —— 這個任務 23–33 次呼叫就結束,長度不足以觀察漂移 |

**先前那一列「五個 run 有四個跑進 harness 目錄」是探針假象**(探針的 cwd 自己帶著
harness 名稱)。換成路徑乾淨的真實專案後,L1 在六個 run 裡沒有再發生過一次。
**L3 仍然沒有量測** —— 需要一個做不完就得換回合的任務,不是更多資料的任務
(「不能用更多資料把任務變長」 的教訓:40 個檔案被一個 for-loop 三步做完)。

---

## 2026-08-12:一個真實 session 五步撞到三個缺陷

擁有者隨手在 `D:/MyProject/DiscoverTurth` 開了一個 session,問一個十項的調查請求。
五次呼叫,把這個 harness 最核心的承諾整條打斷 ——
脈絡與修法:[docs/case/2026-08-12-the-name-nobody-could-load.md](docs/case/2026-08-12-the-name-nobody-could-load.md)

```
1 read  ~/.pi/agent/skills/research-task-routing/SKILL.md
2 read  ...\external\superpowers\skills\planning-with-files\SKILL.md   ← ENOENT
3-5 web_search × 3            injections: none   refusals: none
```

| # | 缺陷 | 修法 |
|---|---|---|
| 1 | 我們自己的指示叫 `planning-with-files`,註冊的是 `pi-planning-with-files` —— **每一條方法論路由都指向載不到的名字** | 全部改成註冊名;`tests/test_skill_names_resolve.py` 從此要求「指示叫得出的名字必須註冊得到」 |
| 2 | `task_plan.md`(8/6 寫的)讓路由器對一個全新的十項請求閉嘴 | 只有 **session 開始之後**寫的計畫才算計畫;不加「幾天算過期」的門檻 |
| 3 | `name: "yes"` 被讀成含引號 → 每次啟動都警告一個正確的檔案 | frontmatter 脫**成對**引號;不成對的不脫 |

**這一天真正的教訓:我自己安排的九個 run 一個都沒發現這三件事。**
它們全部跑在 `PiTaskLab`,那是 C.A.S.E. 專案,`isCaseProject` 為真,
路由器與 `planning-with-files` 這條路**在那裡本來就會讓位** —— 三個缺陷剛好全在盲區。
**自己安排的場地會遺傳自己的假設;要找缺陷,真實使用勝過受控實驗。**

---

## Task Queue

> **2026-08-11 起的排序原則(Round 14 TOWS):**
> SO 先做(用現成工具鏈在真實專案做乾淨實驗)→ WO 次之(校準參數移出程式碼)→
> ST 是紀律不是任務(任何 pp 宣稱必須附 model+harness 配置與樣本數)→
> WT 是排序原則(便宜且二元的先做,昂貴的量測往後)。

### ✅ T-A1 — A+C 的第一個乾淨實驗(**DONE,2026-08-11 Path A 核可**)
* **為什麼**:五個探針 run 全部在被污染的暫存路徑裡、用我隨手寫的 recipe。
  **「一份認真的任務包在真實專案裡被完整執行」——一次都沒測過**,
  而那正是擁有者從頭到尾要的東西
* **服務哪一層**:**L1 + L2 同時**,也是 A(本機模型執行)+ C(強模型寫任務包)的第一個樣本
* **Local DoD**:
  - [ ] 在**真實專案**(非暫存目錄、路徑不含 harness 名稱)建一份認真的任務包
  - [ ] Pi 執行,**不預先告知 cwd**(不作弊)
  - [ ] `mine-session.py` 體檢:認領位置、注入送達、拒絕分布、最終狀態、交付物
  - [ ] **記錄配置**(模型 + harness commit),依 Harness-Bench 的配置層原則
* **成敗判準**:走到 REVIEW **且** Local DoD 的檔案存在。
  失敗也是結果 —— 但這次失敗的原因不會是路徑

**實驗場地(2026-08-11 建立):`D:/MyProject/PiTaskLab`**,
來源在版控裡:[experiments/pitasklab/](experiments/pitasklab/README.md)
(`make-lab.py --out <path>` 重建;**路徑含 `harness` 會被拒絕**)。
復盤時補的:今天所有數字原本都由 `/tmp` 與 session 暫存區的腳本產生,
跑在一顆曾經斷線的抽取式磁碟上 —— 場地一消失就全部不可重現。

* **路徑刻意不含 harness 字樣** —— 這是先前四次失效的成因,已驗證
* 憲法 + Roadmap + 一個任務包(`Task_001_ConfigDrift`)
* 種子資料 8 個 JSON,**標準答案先算好**寫在 gitignored 的 `.ground-truth.json`:
  `timeout` 偏離 = svc-03、svc-06;`retries` 偏離 = svc-04、svc-08。
  **不是事後看模型寫什麼再判斷**
* 任務包的 Local DoD **六條全部可機械判定**(檔案存在、四個標題、格式、data/ 未被修改)
* **提示不提 cwd、不提任務名稱** —— 「請處理 02_Task_Queue 裡待辦的任務」

**配置紀錄(Harness-Bench 配置層原則):**
`harness commit 66628da` / `model GRM-3.2-Sky-ONYX-balanced.gguf`

**這一天的完整復盤:[docs/case/2026-08-11-retro.md](docs/case/2026-08-11-retro.md)**
(三個缺陷同一個形狀、寬容的 catch 吞掉致命錯、fixture 分不出兩種世界、
誤擋花掉的是呼叫數不是結果、一句話不是機制、任務太簡單量到的就是任務、
我自己違反了 fixture 必須可重建、查證前提是最划算的一步)

**三個 run 的結果(同一配置):11/11、11/11、1/11**

第三個 run 走到 `REVIEW`,資料夾是空的 —— 沒有 `output.md`。
挖 session 的呼叫序列:

```
 18 write output.md content="## 多數值\n\ntimeout_ms 多數值:3000…   ← 完整報告
    !! C.A.S.E. 階段閘(CLAIM):這個佇列有 PENDING 任務,還沒有人認領。
 19 write status.txt content="IN_PROGRESS\n"
 20 write status.txt content="REVIEW\n"                              ← 應該被擋,沒擋
```

**兩個獨立缺陷,兩個都已修並附行為測試**
(脈絡:[docs/case/2026-08-11-dod-guard-was-dead.md](docs/case/2026-08-11-dod-guard-was-dead.md)):

1. **驗收物守衛從來沒有生效過。** 呼叫寫成 `missingDodArtifacts(taskDir, _cwd, …)`,
   而 `_cwd` 只存在於 `check()`,不在 `checkTransition()` 的 scope —— 每次 REVIEW 寫入
   都拋 `ReferenceError`,被旁邊那個「recipe 讀不到就 fail open」的 `catch` 吞掉。
   **為某一種失敗寫的寬容 catch,吞掉了另一種致命的失敗。**
   舊測試綠燈的原因:單元測試直接呼叫純函式(它一直是對的),接線測試斷言
   **原始碼字串**含有那個呼叫(它確實含有)。本週第五次「在原始碼文字上斷言」。
2. **拒絕會把內容丟掉,而沒有人講。** 第 18 呼叫帶著完成的報告被 CLAIM 閘拒絕,
   模型認領之後**再也沒有重寫**。閘的措辭現在明講「剛才那次寫入的內容沒有被保存」。

**修好之後重跑兩次(harness commit `7a30060`,同一模型):run 4 = 11/11、run 5 = 11/11。**

| | run 4 | run 5 | run 6(誤擋修好後) |
|---|---|---|---|
| DoD | 11/11 | 11/11 | 11/11 |
| 時間 | 2 分 28 秒 | 3 分 58 秒 | 2 分 56 秒 |
| 工具呼叫 | 23 | 33 | 25 |
| 拒絕 | 階段閘 2 | 階段閘 2、containment 2、loop guard 1 | 階段閘 2 |

* **CLAIM 閘的新句子起作用了。** run 4 的 call 15 帶著報告被擋(訊息含「剛才那次寫入的內容
  沒有被保存」),模型認領後**在 call 19 重寫了報告** —— 這正是 run 3 沒做的事
* **PLAN 閘**兩個 run 都要求先有帶 `## Self-Review` 的 `planning.md` 才准寫 `output.md`
* **驗收物守衛在 run 4/5/6 全程沒開口**(進 REVIEW 時產出都在),
  **但在 run 7 第一次真的擋下了** —— 見下方 T-A2 的紀錄。live 生效已證明
* **run 5 抓到一個誤擋(已修)**:兩次只讀的 `python3 -c "…glob.glob('data/*.json')…"`
  被 containment 判成寫入 `/*.json` —— 路徑樣式的 `\/` 分支會從 token 中間開始比對。
  代價是模型改用寫暫存腳本的迂迴,多花約十次呼叫(33 vs 23)。加錨點後,
  拿掉錨點會且只會讓那三個新案例變紅
* **一個未解釋的觀察**:run 5 的 call 20 寫 `_verify_tmp.py` 回報
  `Successfully wrote 377 bytes`,兩次呼叫後 `ls` 找不到該檔,重寫才成功。
  bridge 沒有刪除任意檔案的程式碼。PiTaskLab 位於 D:(SD 卡,已有中途斷線的紀錄)。
  **不下結論**;若再現就是量測完整性問題,不是模型問題

留下的規則:**守衛「接好了」的定義是它的公開入口會拒絕**,不是輔助函式回傳正確清單,
也不是呼叫出現在檔案裡。fixture 的名字必須符合production 比對的樣式 ——
第一版替換 fixture 用了 `Task_001`,不符 `^Task_(\d+)_`,於是**每一個** status 寫入
都被放行(包括字串 `bogus`),測試失敗的理由是錯的。

### ✅ T-A2 — 校準參數移出出貨程式碼(**DONE,2026-08-11 Path A 核可**)
* **為什麼**:`MAX_REFUSAL_TURNS=8`、重述門檻 `12`、清單上限 `5` 都是對**這一個模型**
  校準的,卻寫在協定執行碼裡。Harness-Bench:能力是 **model–harness 配對**的屬性
* **風險形狀**:換模型時**不會報錯,只會安靜地不合適**

**前提查證(動手前):帳本的說法有一半已經過時。**
`MAX_REFUSAL_TURNS` 早就有覆蓋路徑(`caseClaimRefusalTurns`,經 `resolveFlag`,
專案只能在 8–12 內調緊)。真正還硬編的是:**全域檔裡根本沒有這個 key**,
所以 session snapshot 永遠是空的、程式碼常數是唯一會被用到的值;
以及重述門檻與清單上限完全沒有覆蓋路徑。

**做了什麼**(決策與取捨:[decisions/2026-08-11-calibration-layer.md](docs/decisions/2026-08-11-calibration-layer.md)):

* 四個值進 `pi-config/harness-config.json`,各附 `_key` 說明與量測日期:
  `caseClaimRefusalTurns` 8、`goalRestateThreshold` 12、`goalRestateMax` 2、
  `queueListingCap` 5。**沿用既有的 config + gitignored local 覆蓋機制,沒有新增第二套**
* 程式碼常數留作 fallback;`0`、`"12"`、`true`、`2.5`、負數一律拒收
* **反轉了一條有文件的決定**(`refusalTurns` 的「刻意不讀全域」),原文引在註解裡沒有刪
* **寫下沒搬的與為什麼**:結構性上限(256 字元欄位、200k 掃描預算)不隨模型變;
  迴圈守衛的 4/3/2 **可能真的是校準,但不在這次的清單裡** —— 附觸發條件
* `calibrated()` 另立 `calibration.ts`:`index.ts` 開頭是 `require.resolve`,
  bare node 載不動,測試會死在 import 而不是斷言

**順帶取得 T-A1 缺的那塊證據:run 7(11/11,28 呼叫,3 分 12 秒)。**
它走了和 run 3 完全相同的失敗序列,而這次被擋住:

```
20 write output.md             !! 階段閘(CLAIM):任務還沒認領 —— payload 被丟棄
21 write status.txt = IN_PROGRESS
22 write planning.md
23 write status.txt = REVIEW   !! C.A.S.E. 驗收物守衛:…點名的檔案還不存在:output.md
24 read  output.md             ENOENT(模型自己去確認)
25 write output.md             ← 重寫交付物
26 write status.txt = REVIEW   允許
```

模型自己的話:*"The output.md wasn't persisted from the earlier attempt. Let me write it now"*。
**run 3 在第 23 步結束成空的 REVIEW;run 7 在同一步被擋下,然後把事情做完。**
這是驗收物守衛的第一次真實 session 證據 —— 距離它被寫出來一天,距離它被發現從未生效幾小時。

**測試的教訓,今天第二次:** 出貨值與 fallback 是同一個數字,只驗出貨情境**分不出
「讀了 config」與「根本沒讀」**。第一版驗了 `listingCap()` 這個輔助函式 ——
把呼叫點改回 `slice(0, 5)` 之後**十條全綠**。加了 `useHarnessRoot()` 接縫、
改從 `check()` 的拒絕文字驗,同樣的破壞才會紅。

### ✅ T-A3 — 合併目標重述與任務憲法(**DONE,2026-08-11 Path A 核可;live 送達已於 T-A6 的 run 9 證明**)
* **為什麼**:Round 14 認定兩者**功能重疊**。重述目前重述整段使用者請求,
  應改為當前任務的 Local DoD
* **依賴**:T-A1 的結果

**前提查證的結果比帳本更根本:**

* 真實 C.A.S.E. 提示「請處理 02_Task_Queue 裡待辦的任務」被分類為 `multiStep: false`
  → **目標重述從來沒有在任何 C.A.S.E. run 裡啟動過**(run 4–8 的注入表可證)
* 就算啟動,它重述的是那句提示 —— **完全沒有講到目標**
* `restate.begin()` 原本在 `isCaseProject` 的 return **之前**,所以在 C.A.S.E. 專案裡
  打一段長提示會拿到原始提示,而不是任務的 Local DoD

**做了什麼:**

* case-bridge 新增 `TaskGoalRestate`,來源是**被認領任務的 Local DoD**
  (沒有 DoD 才退回 Objective),在同一個 `tool_result` 通道上與憲法、階段通知並列
* task-shape 那支在 C.A.S.E. 專案**明確讓位** —— 「關掉」與「碰巧沒開」是兩回事
* 兩者共用同一組校準值(`goalRestateThreshold` / `goalRestateMax`),T-A3 之後
  它們是**一個機制、兩種來源**,由專案型態決定
* 重複認領同一個任務**不重新武裝**:`claimedTaskDir` 對每一次讓 status 停在
  IN_PROGRESS 的成功寫入都回傳,若每次都歸零,**重複最多的 run 反而最安靜**

**live 結果:沒有觸發,而且 session 說得出原因。**
run 8(11/11,24 呼叫,2 分 54 秒):認領在第 18 步,run 在第 24 步結束 ——
**認領之後只有 6 個工具結果,門檻是 12。**
不調門檻:12 是為「從 prompt 起算」校準的,而這裡的時鐘是「從認領起算」,
兩者不是同一個量。**要驗證它,需要的是一個夠長的任務,不是一個更小的數字。**

* 機制:已接線、單元行為已證(9 條,含錯誤不計數、重複認領不歸零、換任務換目標)
* **live 送達:未證**。這是 T-A5/L3 的前置,不是可以靠調參數繞過的
* 順帶:**驗收物守衛連續第二次**擋下同一個失敗(run 8 第 20 步 REVIEW 被拒 →
  第 22 步重寫 `output.md` → 第 24 步通過)

### ⚪ T-A4 — tool-vs-text 歧義(**降級,不刪**)
* **為什麼**:文獻 26.5–54%,**我們自己量到 2.5% 回合 / 6% session** —— 真實但非主因
* **修法屬於推論服務端**(`tool_choice`、GBNF 約束解碼),不在 bridge
* **觸發條件**:若 T-A1 的失敗與此有關,升級

### ✅ T-A6 — 夠長的任務(**DONE,2026-08-11 Path A 核可**)
* **為什麼**:連續五個 run 11/11,證明的是**任務太簡單**,不是機制有效。
  Task_001 認領之後只剩 6 個工具結果,而重述門檻是 12 ——
  **T-A3 的 live 驗證與 L3(續航)都卡在同一件事:沒有一個夠長的任務**
* **長度不能來自更多資料**(已在案的疤:40 個檔案被一個 for-loop 三步收掉)。
  只能來自**不可批次的步驟** —— 下一步的目標必須由上一步的輸出才能知道
* **形狀**:`Task_002_ConfigRepair` —— 驗證器 `check.py` **一次只報一個違規**,
  修好一個才看得到下一個。16 個服務、11 個植入缺陷、7 條規則,
  每條規則的正確修法唯一(所以標準答案可機械判定)
* **場地已建好並驗證**:
  - 未解狀態評分 **2/9**(評分器會失敗,不是永遠 PASS)
  - 把標準答案套上去 → `check.py` 離開碼 0、`ALL OK`(任務可解)
  - 套用是在 `/tmp` 的複本上做的,原地仍是壞的
* **Local DoD**:
  - [ ] run 的**認領後**工具結果數 ≥ 12(這是這個任務存在的理由)
  - [ ] `mine-session.py` 體檢:認領後長度、注入分布、拒絕分布
  - [ ] 記錄 `task goal restatement` 有沒有觸發 —— **有或沒有都是結果**
  - [ ] 對照標準答案的 9 條驗收
* **預先寫死的失敗條件**:若模型仍然用一次批次收掉(例如自己讀 `check.py`
  推出全部違規再一起改),**那就是這個設計輸了**,而不是再加規則 ——
  下一步改成「驗證器的訊息本身不可預測」而非「規則更多」

**run 9 結果(harness commit `13dac68`):9/9 DoD,11 輪一輪不差,6 分 07 秒。**

| | Task_001(前八個 run) | Task_002(run 9) |
|---|---|---|
| 工具呼叫 | 23–33 | **57** |
| 助理回合 | 15–23 | **47** |
| 認領後的工具結果 | 6 | **遠超過 12** |
| 錯誤結果 | 3–7 | 16(多數是 `check.py` 依設計離開碼 1) |

* **設計成立:模型沒有批次收掉。** 它一輪一輪跑驗證器、讀訊息、只改那一個欄位,
  11 輪全部照做,而且 `fixlog.md` 的 11 個區塊每一個都有四個欄位、訊息都以 `R` 開頭
* **T-A3 的 live 送達證明:`task goal restatement 2`** —— 分別落在第 31、48 次呼叫,
  內容是這個任務真正的 Local DoD。**這是那個機制第一次真的送到模型面前**
* **上限起作用了**:兩次就停,沒有變成壁紙
* **錯誤不計數的設計在這裡看得最清楚**:16 個錯誤結果裡多數是驗證器的離開碼 1,
  它們不推進計數器 —— 所以第一次重述發生在第 31 次呼叫,而不是第 12 次
* `check.py` / `teams.json` / `defaults.json` 的 md5 一個字沒變(role.md 明講不准動溫度計)

### 🔵 T-A7 — `cd 出去 && 執行`:相對路徑會跟著 cd 走(**認領中,2026-08-12 新增**)
* **為什麼**:run 10(驗收 session)第 23 呼叫 `cd harness_repo && node <腳本>`,
  在**別人的專案**裡建了 `wiki/` 與 `skills/`。守衛看不到任何路徑,因為
  `node <腳本檔>` 不是重導向、不是複製、也不是內嵌程式碼。**`cd` 才是徵兆**
* **同一個破口更容易發生的寫法**:`cd D:/other && echo x > notes.md` ——
  相對路徑被解析到 session 的 cwd,判為「在專案內」
* **第二個成因(不同層)**:mece-autopilot 的技能叫模型執行
  `node scripts/mece-autopilot-orchestrator.js` —— **相對路徑,而腳本只存在於 harness**。
  模型要照做只能走到 harness。**守衛擋越界,擋不住指示把人往界外送**
* **脈絡**:[docs/case/2026-08-12-cd-out-and-run.md](docs/case/2026-08-12-cd-out-and-run.md)
* **先寫死的失敗條件**:任何修法若讓 `cd /tmp && ls`、`cd other && git log`
  這類**唯讀**指令被擋,就是輸了 —— 這個 repo 有一個因誤擋被永久關掉的守衛(GateGuard)

**做了什麼(兩層都動,因為成因有兩個):**

* **邊界** —— `bash-containment.ts::relocatedWrite`:逐段追蹤 `cd`,
  一旦當前目錄離開專案且該段**可能寫入**就拒絕。
  「可能寫入」用的是**唯讀白名單的補集**(寫入的形式無界,而在別人目錄裡合法要做的事
  只有「看」),`git` 另判子指令,`sed`/`perl` 另判 `-i`,唯讀指令帶重導向也算寫
* **誘因** —— `mece-autopilot-bridge/notice.ts`:注入文字現在明講
  **「在你自己的工作區跑,不要 cd 進 harness」**,並把
  `wiki/.mece_state.json` 那句的相對路徑錨定成「**在你的工作區裡**」。
  文字抽成獨立模組才測得到 —— `index.ts` 開頭是 `require.resolve`,測試載不動
* **破壞驗證**:關掉 `relocatedWrite` → 紅 7 條(含 run 10 的原始指令);
  唯讀那幾條**一條都沒紅**
* **`/tmp` 的坑**:`isScratch` 的前綴帶結尾斜線,所以 `/tmp/x.log` 是 scratch、
  裸的 `/tmp` 不是。第一版因此把 `cd /tmp && node build.js` 擋掉 ——
  **正好是預先寫死的失敗條件**,由 `isScratchDir` 用哨兵子路徑重用既有述詞修正

### ⚪ T-A8 — 「先規劃再搜尋」:建議送達了,順序沒改
* **為什麼**:run 10 判準三沒過 —— `routing note` 送達,模型仍先搜兩次才寫 `task_plan.md`。
  對照 run 4 / run 7:**同一句話一次有效一次無效。一句建議不是機制**
* **不要直接加閘**:閘會製造新的規避形狀(引用閘把 URL 0→10 的同時把捏造 0→4)
* **觸發條件**:T-A7 完成後,先量「先搜再規劃」在真實 session 的發生率,再決定要不要動

### ⚪ T-A5 — 噪音底線(Global DoD 第 6 條)
* **為什麼**:同題同臂 42 vs 4。**所有效果宣稱的天花板**;不擋缺陷修正

### 已擱置(附觸發條件)
* **技能位置遷移** —— 解的是探針假象。設計保留於
  [decisions/2026-08-11-skill-location-migration.md](docs/decisions/2026-08-11-skill-location-migration.md);
  **真實專案出現 harness 路徑污染時重啟**
* **反轉極性** —— 需要誤擋先驗,而先驗要靠真實使用累積
* **T1b 其餘 31 個未掃描模組** —— 便宜但非阻塞

---

## 舊 Task Queue(2026-08-10,已被上方取代)

> 規則:**一次認領一個**。做完 → 驗收(附實際指令與輸出)→ 復盤 → 有發現就加 task → 再認領下一個。
> 每一條都要寫**為什麼**,而且要指得出它服務哪一層目標。

### ✅ T1 — 檢查形狀稽核(**已完成 2026-08-10**)
* **為什麼**:一天之內出現**三次**「檢查不會失敗」——
  46 條圍堵測試判 `!== null`、三條路由測試被 fallback 蓋過、
  「repo 沒被污染」查的是看不到 gitignored 的 `git status`。
  **是模式不是巧合。** MECE Round 12 面板判定**優先於新功能**
* **服務哪一層**:全部三層的**前提** —— 檢查會說謊的話,其餘結論都不可信
* **Local DoD**(逐條驗收):
  - [x] 掃出弱檢查清單 —— 143 個候選,收斂到 15 個「拒絕存在但不驗內容」
  - [x] 每一條給處置 —— **而處置的結論推翻了做法本身,見下**
  - [x] 蓄意破壞驗證 —— **做了反事實,結果是我的強化一條都沒多抓到**
* **驗收證據**:`Ran 1288 tests, OK`;`check-guard-mutations.py --cap 4` → 17 模組 0 存活者

**復盤:T1 的結論與它的假設相反。**

1. **強化斷言買不到東西。** 我把 6 條 `assertIsNotNone` 換成「斷言是哪個階段拒絕」,
   然後做反事實(破壞程式碼 × 有/無強化):**25 對 25,強化獨力抓到 0 條** ——
   因為姊妹測試早就斷言了內容。**強化斷言不等於改進,只有在別人抓不到時才算。**
2. **真正找到弱檢查的一直是變異掃描。** 當天三個真實弱檢查
   (`block: true`、路由 fallback、上限)全是掃描找到的,沒有一個是讀斷言風格找到的。
3. **所以槓桿是掃描的覆蓋率,不是斷言的措辭。** 量出來:**48 個純模組,33 個從未被掃過。**
   納入決策路徑上的兩個(`shape.ts`、`plan.ts`)後**立刻冒出 22 個存活者**,
   其中 10 個在我當天才改過的 `plan.ts`。
4. **順帶抓到一個真的分類器偏誤:** `text.length < 25` 是照英文校準的,
   而中文每字元的內容量約兩倍。「研究並比較三個競品的定價與功能差異,並整理成表格」
   24 字,**在看任何訊號之前就被丟掉**。已改成加權長度(CJK 算 2)。
   **但誠實說:真實歷史上 18/106 的多步比例修改前後完全一樣 ——**
   那 6 則卡在線下的中文提示本來就不是多步。**原理對,目前零效果。**

**新增的 task(依規則「有發現就增加」):見 T1b。**

### ⚪ T1b — 其餘 31 個未掃描模組
* **為什麼**:T1 量到 48 個純模組只有 15 個在掃描裡。納入 2 個就找到 22 個存活者,
  其中 10 個在當天改過的檔案。**剩下 31 個是未知的**
* **服務哪一層**:全部三層的前提(同 T1)
* **Local DoD**:逐一評估納入或寫明為何不納入(例如 `async-exec-bridge/*` 用 bun 測試,
  與這個掃描器的 python 測試模組對不上)
* **成本**:中。掃描很慢,要分批

### ⚪ T2 — 導航修法量測(三輪)+ 誤擋先驗
* **為什麼**:Round 12 的「第二次拒絕時印出工作目錄」上線後,
  **模型第一次自己回頭**(n=1),但下一個 run 又跑回去。
  Round 13 同時要求量誤擋先驗,因為 T3 不能沒有它就上線
* **服務哪一層**:**L1** —— 這是主要失效模式的直接量測
* **可證偽預測(已寫進程式碼)**:三輪內 harness 佇列的認領應下降、工作區佇列應上升。
  **三輪都沒變 = 第四次失敗的加字,改走結構**
* **Local DoD**:
  - [ ] 三個真實 run,同情境同提示
  - [ ] 用 `mine-session.py` 逐一體檢,記錄認領位置
  - [ ] 記錄期間所有被擋的合法工作(誤擋先驗)
* **成本**:三輪 × 最多 25 分鐘

### ⚪ T3 — 反轉極性(唯讀白名單)
* **為什麼**:圍堵六輪被繞過,根因是**枚舉「會寫檔的形式」是無界的**。
  cua 的 deny-by-default 指出正確極性
* **服務哪一層**:**L1 的安全網**(不是根因,根因是 T2)
* **擋住它的東西**:**必須先有 T2 的誤擋先驗。**
  這個 repo 已經有一個因為誤擋被永久關掉的守衛(GateGuard)
* **先寫死的失敗條件**:真實 run 出現誤擋且嚴重到讓人想關掉守衛 → **設計輸了,不是再加例外**

### ⚪ T4 — 驗收物守衛的真實驗證
* **為什麼**:已實作、0 變異存活者,**但從沒在真實 run 響過**。
  照本 repo 的標準,那叫未驗證
* **服務哪一層**:**L2**
* **Local DoD**:一個真實 run 走到「想進 REVIEW 但沒有交付物」並被擋,session log 為憑

### ⚪ T5 — 探針殘留清理(**需要擁有者決定**)
* **為什麼**:`02_Task_Queue/Task_001_Inventory/` 是 2026-08-10 探針寫進 CK repo 的,
  6 個檔案。我們花整天防未來的污染,**沒清掉自己造成的**
* **服務哪一層**:誠信。而且它同時是模型的**誘餌**(L1)
* **擋住它的東西**:那是 CK 的工作目錄,**刪除要他決定**

### ⚪ T6 — Task_020 `[H]` Handoff Capsule
* **為什麼**:協定 §16 明文要求,**我們完全沒實作**。長 run 壓縮後接不上
* **服務哪一層**:**L3**
* **擋住它的東西**:L1 沒過的話,長 run 根本走不到需要 capsule 的地方

### ⚪ T7 — Task_021 learnings 注入 / T8 — Task_024 重述換內容源
* **為什麼**:`[T]` 反重複沒實作;目標重述目前重述的是整段使用者請求而非當前任務
* **服務哪一層**:**L3**
* **擋住它的東西**:同 T6

### ⚪ T9 — 噪音底線量測(Global DoD 第 6 條)
* **為什麼**:同一提示同一臂量到 **42 vs 4 次工具呼叫**。
  在這種變異下,任何「效果」宣稱都不成立
* **服務哪一層**:所有**效果**宣稱的前提(不是缺陷修正的前提)

**排序理由:T1 是全部的前提(檢查要先可信),T2 是 L1 的直接量測且擋著 T3,
T4 便宜且可順帶做,T6–T8 都被 L1 擋住,T9 只擋效果宣稱。**

---

## 方法:為什麼改成「批次改 + 深挖一份 log」

2026-08-10 統計本段工作的實際產出:

| 方法 | 花費 | 產出 |
|---|---|---|
| A/B 實驗(漂移 v1、v2) | 7 個真實 run + 3 次情境設計 | **0 個結論** |
| 深讀 session log | 4 份 | **6 個真實缺陷** |
| 變異掃描 | 4 個模組 | 4 個缺陷 + 1 段死碼 |
| 蓄意破壞 | ~20 次 | 驗證了每一個守衛 |

**關鍵區分:控制變因只有「量效果」需要,「找缺陷」不需要。**
`cp a b 2>/dev/null` 讓目的地消失,這是不是缺陷跟同時改了幾件事無關。
我們大部分工作是找缺陷,卻一直付量效果的價錢。

**已做成工具:`python scripts/mine-session.py --latest [--full]`。**
它跑的就是那四次手動深讀的固定清單:輪次與呼叫數、批次形狀、
哪些注入真的送到模型、哪個守衛拒絕了幾次、**連續拒絕是否逐字重複**、
**模型有沒有自己讀過被注入給它的檔案(歸因混淆)**、以及完整工具序列。

驗證方式是拿**已知答案的 session** 對照 —— 對那個跑錯 repo 的 run,
它自動報出 `phase gate 9 / containment 1 / harness-root hint 1 / tool-first 1`
與「4 次拒絕與前一則逐字相同」,與我手動查出的完全一致。
fixture 是從真實 session **切出來的連續片段**,不是編的。

---

## 方法論缺口(2026-08-10 查證 → **已修**)

擁有者問:subagent 領 local 任務時,有沒有 planning 與 superpowers 方法在執行?
**答案是沒有,而且是三個獨立缺口。**

| # | 缺口 | 證據 |
|---|---|---|
| 1 | **路由器分類的是使用者訊息,不是任務** | `task-shape-bridge/index.ts:110` 是 `classifyRequest(event.prompt)`。佇列 run 的使用者訊息是「繼續」,而多步的工作寫在 `recipe.md` 裡,路由器從來沒讀過它 |
| 2 | **兩套計畫系統互不認識** | `plan.ts:55` 的 `hasAnyPlan` 找的是 `task_plan.md`;C.A.S.E. 任務寫的是任務包裡的 `planning.md`。專案根目錄有一份 `task_plan.md`,佇列裡每個任務的路由提示就全被抑制 |
| 3 | **任務層完全沒有方法論路由** | 階段閘的 PLAN 拒絕說的是「寫 planning.md(步驟、檔案、驗證方式 + Self-Review)」—— 那是**範本**,不是**方法**。沒有任何注入說「除錯用 systematic-debugging、新工作先 brainstorming」,而那是 `CLAUDE.md` 與 `AGENTS.md §10` 的規定 |

### 修法:讓位,而不是搬分類器

兩個 bridge 是同層安裝、彼此沒有相依,**沒有跨 bridge import 的先例**;
而重造分類器是本 repo 已經犯過的錯。所以修法是:

* **路由器在 C.A.S.E. 專案裡讓位**(`plan.ts::isCaseProject`)——
  它的 routine 說「寫 `task_plan.md`」,而 C.A.S.E. 任務要的是任務包裡的 `planning.md`。
  **它在 C.A.S.E. 專案裡給的建議本來就是錯的**,所以缺口 1 與 2 一起消失,不需要分類器。
  這與階段閘讓位給目錄圍堵是同一個模式:**誰有更具體的抱怨誰講話,而且只有一個講得到。**
* **方法論寫進任務專屬憲法**(`task-context.ts::methodology`)——
  在認領那一刻、走已證明送得到的通道。依任務 Objective 的少數字面訊號
  挑 `systematic-debugging` / `brainstorming` / `test-driven-development`;
  **沒命中時給出完整路由規則,不是沉默**(沉默會被讀成「不需要方法」)。
  `planning.md` + `## Self-Review` 那一半**永不隨關鍵字而條件化** ——
  階段閘無論任務長什麼樣都會擋。

證據:`Ran 1210 tests, OK`;四個蓄意破壞全紅;變異掃描 `--only task-context --all` **0 存活者**;
`verify-bridges.py` 13 bridges 0 failures。

**過程中修掉一個我自己寫的假測試**:三條路由測試原本只斷言「技能名出現過」,
而沒命中時的 fallback 會列出全部三個 —— **刪掉路由規則測試照樣綠**。
改成斷言「有沒有真的路由」(前綴 + 該前綴之後的內容),三個分支現在都咬得住。

**關於 subagent:** 目前**沒有**每個任務開一個子行程的機制。
若要做,子行程有自己的 user prompt,`before_agent_start` 會重跑 ——
**缺口 1 會自動被修掉**,因為子行程的提示就是任務描述。
但 Pi 自己的 subagent 範例用 `--no-session`,那會廢掉本 repo 的驗證紀律,必須改用 `--session-dir`。

---

## 進度真實狀態(2026-08-10 逐條查證)

> **注意:`01_Roadmap/roadmap.md` 的勾選框是壞的** —— 18 個 `- [ ]` 裡約 8 個內文已寫
> `DONE` / `REVIEW`,只是從來沒打勾。要看真實狀態請看這一節。

### 已完成並驗證
| 項目 | 證據 |
|---|---|
| 目錄圍堵(write/edit/bash) | [Task_004](docs/case/task-004-case-guard-bash.md)、[Task_013](docs/case/task-013-write-forms.md) |
| cwd 混淆重導提示 | [Task_003](docs/case/task-003-cwd-confusion.md) |
| 研究深度守衛 | [Task_005](docs/case/task-005-research-depth-bash.md) |
| 被擋呼叫的矯正器 | [Task_010](docs/case/task-010-blocked-claim-vocabulary.md)、[Task_011](docs/case/task-011-blocked-claim-channel.md) |
| 階段閘 + 階段開放通知 | [Task_016](docs/case/task-016-phase-tool-gate.md) |
| Path A 人類驗收 | [Task_018](docs/case/task-018-path-a-human-review.md) |
| 推進器 settled 迴圈 | [Task_015](docs/case/task-015-advancer-settled-loop.md) |
| 佇列推進器 | [Task_001](docs/case/task-001-queue-advancer.md) |
| Checker pass | [2026-08-08](docs/case/2026-08-08-checker-pass.md) |
| 推進器預設值建議 | [2026-08-09](docs/case/2026-08-09-advancer-default-recommendation.md) |

### 做了但沒有結論
| 項目 | 狀態 |
|---|---|
| `Task_019` 目標重述 | **送達已證明,有效性三次量測都測不到** — [預先登記與三次結果](docs/measurements/2026-08-09-task019-preregistration.md) |
| `Task_023` 任務小憲法 | **送達已證明,行為影響未歸因**(模型在認領前自己讀了 role.md)— [文件](docs/case/2026-08-10-task-local-constitution.md) |
| `Task_022` 漂移 A/B | 7 個 run,**三次情境都造不出會漂移的對照組** |

### 尚未開始(9 項,2026-08-10 修好勾選框後的實數)
`Task_012` 守衛形狀稽核 / `Task_014` 上游回饋 / `Task_020` Handoff Capsule /
`Task_021` learnings 注入 / `Task_024` 重述換內容源 /
`Task_006` Layer 1 可達性 / `Task_007` catalog 分級 / `Task_009` 舊議題重評

> 勾選框已於 2026-08-10 逐條核對修正:6 項內文寫著 DONE/REVIEW 卻沒打勾,已補;
> `Task_001` / `Task_015` 補上完成註記;`Task_022`(結論為「測不到」)與
> `Task_023`(送達已證明、影響未歸因)改為已完成並註明真實狀態 ——
> **「已跑出否定結果」不是待辦。**

### 其他缺口
* **Global DoD:3 條 ❌、1 條 ⚠️** — [global_dod.md](01_Roadmap/global_dod.md)。
  第 6 條(噪音底線未量測)是所有 A/B 結論的前提,至今未做
* **Prior art:37 個來源,16 個未審視** — [REGISTER.md](docs/prior-art/REGISTER.md)
* **新的第 2 階拒絕(帶佇列資料)在真實 run 從未觸發過**

---

## 工作紀錄

### 2026-08-10(第六段) — CI 抓到我、cua 審視、Round 13
**做了什麼:** 修 CI(平台專屬 fixture);審視 cua 並登記;MECE Round 13 重定威脅模型;
修掉兩個守衛對「絕對路徑」的定義不一致。
[Round 13](docs/mece/rounds/2026-08-10_round13_把導航問題當成資安問題.md)・
[cua 審視](docs/prior-art/2026-08-10-cua-review.md)

**收穫:**
* **我們從來沒有沙箱** —— 唯一邊界是解析字串的守衛。而 Pi 自己
  (`dist/bun/restore-sandbox-env.d.ts`)預期**在外部沙箱裡跑**,擴充層沒有任何權限機制
* **cua 唯一可移植的是極性:deny-by-default。** 而關鍵不是 fail-closed,是
  **哪一半是無界的** —— 枚舉「會寫檔的形式」無限,枚舉「唯讀指令」有界
* **這是導航問題,不是資安問題。** 模型先迷路,**被擋之後才開始規避**
  (`ECC_GATEGUARD=off`)。強化邊界會製造它要防的行為
* **CI 是對的,我的 fixture 是錯的** —— `D:/...` 在 Linux 是相對路徑。
  而修完測試才發現**產品碼有同一個病**:containment 認得磁碟機代號,phase gate 不認得,
  **兩個守衛對同一條路徑給相反答案**
* **有些測試只在 CI 上有牙齒** —— 那條跨平台測試在 Windows 上蓄意破壞也不會紅,已寫進 docstring
* **同一處修到第三次,就不是缺陷是設計錯了** —— 我修了六輪才回頭查 prior art,
  而那條規則一直都在

### 2026-08-10(第五段) — MECE Round 12:守衛都對,結果仍然錯
**做了什麼:** 十三角色面板復盤五個真實 run;實作結論一(圍堵從描述改成展示)。
完整討論:[Round 12](docs/mece/rounds/2026-08-10_round12_守衛都對而結果仍錯.md)

**收穫:**
* **不作弊的情況下,五個 run 有四個沒產出交付物** —— 今天修的七項沒有改變這個數字
* **模型不是混淆,是推論** —— 系統提示裡 harness 路徑出現 28 次、cwd 出現 1 次,
  而那個路徑下真的有一個二十個任務的佇列。**它選了證據強的那一邊**
* **修法不是告訴它「你錯了」,是把它缺的那一半證據給它** ——
  第二次拒絕起改成印出工作目錄的實際內容與任務名稱
* **我自己的檢查也在用弱證據下強結論**:`git status` 乾淨就宣布沒污染、
  `!== null` 就宣布守衛有效、只斷言技能名出現就宣布路由正確。**三次,是模式不是巧合**
* **誘餌是開發環境特有的** —— 使用者 clone 後 `02_Task_Queue/` 是空的。
  但 28:1 的證據比例在任何機器上都在

**尚未做(Round 12 的其餘結論):**
* F:檢查形狀稽核(掃現有測試裡不會失敗的弱斷言)—— **優先於新功能**
* B:誘餌是 CK 的工作狀態,**只報告不動手**
* E:噪音底線量測,排 roadmap,不擋缺陷修正

### 2026-08-10(第四段) — 三個守衛各自成功,合起來放行一個空的 REVIEW
**做了什麼:** 體檢真實 run;補上「進 REVIEW 前檢查 DoD 點名的檔案是否存在」。

**收穫:**
* **圍堵修好之後,模型第一次自己回頭** —— 第 9 次呼叫想在 harness repo 建任務包被擋,
  之後回到自己的 cwd 正常工作。前三次都沒有回頭
* **任務憲法終於在真實 run 觸發**,方法論路由挑了 `brainstorming` ——
  **與跑之前寫下的預測一致**
* **但最終狀態是 `REVIEW`,而 `output.md` 與 `planning.md` 都不存在。**
  模型兩次想跳到 DONE,兩次被轉換守衛擋下,於是走了**合法的那條路**到 REVIEW ——
  而合法的那條路不需要任何交付物。**門檻定義規避的形狀,又一次**
* **它其實已經寫出報告了** —— 被擋掉的那次呼叫帶著完整的 retries 對照表。
  認領完成、階段開放通知響了兩次,**它從來沒有重寫 output.md**。工作做完然後丟掉
* **REVIEW 是召喚人類驗收的狀態** —— 照原樣,使用者會被請去驗收一個空資料夾

### 2026-08-10(第三段) — 圍堵被直譯器繞過,而我的驗證看不見
**做了什麼:** 用 `mine-session.py` 體檢真實 run,查出 containment 有六種繞過,全數封閉。

**收穫:**
* **模型被擋兩次之後改用 `python3` 寫檔,成功寫進另一個專案** ——
  一整個任務包(role/recipe/planning/5188 bytes output/status)進了 harness repo。
  `bashContainmentBlock` 只認得 shell 重導向、`tee`、`cp`/`mv`、`mkdir`、`dd`、`sed -i`,
  **不知道直譯器會寫檔**。這是同一類的第四次
* **它先試 `ECC_GATEGUARD=off bash -c ...` —— 主動找繞過**。被擋才改用 python3
* **我當時宣告「repo 乾淨」是錯的** —— 我查 `git status`,而 `02_Task_Queue/` 是 gitignored,
  **那個檢查在結構上看不到它**。驗證方法本身無法證明它宣稱排除的事
* **`block: true` 是物件字面值,不是型別宣告** —— 變異掃描把它翻成 `false`,
  我 46 條測試全綠,因為測試判的是 `!== null`,而 `{block:false}` 也不是 null
* **allowlist 用行號當鍵,一個 session 內位移三次**,第三次在我記錄第二次的十分鐘後。
  已改成**用欄位與運算子比對**,位移只提示不失敗 —— 治因不治症

### 2026-08-10(第二段) — 任務層方法論(Task_025)
**做了什麼:** 路由器在 C.A.S.E. 專案讓位;方法論路由寫進任務專屬憲法;總控文件 `PROGRESS.md` 上線。

**收穫:**
* **兩個機制給相反建議時,先問哪一個本來就不該說話** —— 路由器在 C.A.S.E. 專案裡
  指的是 `task_plan.md`,那個建議從一開始就是錯的。讓位比整合便宜
* **沉默會被讀成「不需要」** —— 方法論沒命中任何訊號時給完整規則,不是不講
* **一個分不出「命中」與「fallback」的測試,不是測試** —— 刪掉路由規則它照樣綠
* **總控文件必須被檢查守著** —— `test_progress_ledger.py` 第一次跑就抓到 11 份沒被連到的文件

### 2026-08-10(上半) — 守衛品質三修 + 儀器缺陷
**做了什麼:** 守衛互撞三項全修;`2>/dev/null` 解析缺陷兩處;`pi --print` stdin 卡死。

**收穫:**
* **`2>/dev/null` 讓兩個抽取器同時壞掉,方向相反** —— 階段閘誤擋無害的 `ls`,
  目錄圍堵放行逃出專案的 `cp`。同一個疏漏,只補過一個地方。
  [文件](docs/case/2026-08-10-guards-collide.md)
* **守衛互撞看起來像優先權問題,查下去是解析器的錯。**
  先問「這些拒絕本來就該發生嗎」,再問「誰該先講話」
* **一個 tool_call 只有一個守衛擋得成,先開口的就是唯一被聽見的。**
  階段閘說「先認領任務」(真的,而且是錯的那句),containment 知道「你在別的專案」卻被跳過
* **`pi --print` 會卡在讀 stdin** —— 兩次 25 分鐘空白被我說成「暫時性」,
  實際是可重現的:`< /dev/null` 就好。**卡住和真實的零長得一模一樣**
* **修法不是多寫幾段話** —— 階段閘手上有佇列絕對路徑,卻背誦路徑的形狀。缺的是資料
* **allowlist 條目會過期** —— 用行號當鍵,上面插程式碼就靜默失配,存活者看起來像新的
* **測試綁在實作拼法上會假性變紅** —— 比對常數名稱、切固定字元數,兩者都咬過我

### 2026-08-09 — 反漂移缺口分析
**做了什麼:** 對照 C.A.S.E. 找出反漂移缺口;`Task_019` 目標重述;`Task_023` 任務小憲法。

**收穫:**
* **`before_agent_start` 每則使用者訊息只跑一次,不是每輪** ——
  實測 1 則訊息 / 16 輪。`CLAUDE.md` 寫錯了好幾週
  [文件](docs/case/2026-08-09-anti-drift-gap-analysis.md)
* **換任務用的是 custom message,不開新 prompt cycle** ——
  所以憲法、Roadmap、小憲法都不會因為換任務而重新出現
  [文件](docs/case/2026-08-10-task-local-constitution.md)
* **每個機制都在回答「這一步准不准」,而漂移問的是「我還在做對的事嗎」**
* **乾淨的 run 無法驗證反漂移機制** —— 沒有病人就證明不了藥
* **不能用「給更多資料」把任務變長** —— 40 個檔案被一個 for-loop 吃掉,3 次呼叫做完
* **同一提示同一臂:42 vs 4 次工具呼叫** —— 一個數量級的變異,小樣本 A/B 無意義

---

## 相關索引

* [反漂移缺口分析](docs/case/2026-08-09-anti-drift-gap-analysis.md)
* [任務小憲法](docs/case/2026-08-10-task-local-constitution.md)
* [守衛互撞](docs/case/2026-08-10-guards-collide.md)
* [Task_019 預先登記與結果](docs/measurements/2026-08-09-task019-preregistration.md)
* [oh-my-pi-can1357 審視](docs/prior-art/2026-08-09-oh-my-pi-can1357-review.md)
* [Global DoD](01_Roadmap/global_dod.md) ・ [Roadmap](01_Roadmap/roadmap.md)

## 其餘紀錄(由 tests/test_progress_ledger.py 維持齊全)

* [佇列推進器:拿掉誘餌之後的重測](docs/measurements/2026-08-06-advancer-clean-rerun.md)
* [佇列推進器:三個 bash 洞補完後的重測與判定](docs/measurements/2026-08-06-advancer-verdict.md)
* [深度閘與產出閘:第一次實測開火](docs/measurements/2026-08-06-depth-and-artifact-gates-live.md)
* [佇列推進器:第一次真實量測](docs/measurements/2026-08-06-queue-advancer-first-run.md)
* [2026-08-08 4b 重測:閘擋住了開場那一擊,而模型從此不再搜尋](docs/measurements/2026-08-08-4b-turn-ramp.md)
* [2026-08-08 推進器重測:迴圈接起來了,而開場那一擊仍然穿過去](docs/measurements/2026-08-08-advancer-remeasure.md)
* [2026-08-09 CLAIM 額度實驗:先下注,再量](docs/measurements/2026-08-09-claim-budget-bet.md)
* [2026-08-09 乾淨重測:迴圈第一次在研究型 run 收斂,而先規劃只成立一半](docs/measurements/2026-08-09-clean-research-runs.md)
* [2026-08-09 階段轉換通知:響了,而且模型恢復搜尋](docs/measurements/2026-08-09-phase-notice-live.md)
* [Measurements](docs/measurements/README.md)
* [技能可達性全掃](docs/measurements/skill-reachability.md)
