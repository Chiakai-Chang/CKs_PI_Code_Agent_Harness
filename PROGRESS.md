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

**已完成:** 任務層方法論(Task_025)、`scripts/mine-session.py`。

**下一步(待擁有者確認):**
1. 跑一個真實 session,用 `mine-session.py` 一次體檢今天全部改動
   —— **目前為止沒有任何 run 認領過任務,所以方法論注入還沒被真實觸發過**
2. 批次處理 Task_020 / 021 / 024(三項都是注入類機制)

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
