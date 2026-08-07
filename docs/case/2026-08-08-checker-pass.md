# 2026-08-08 Checker 核可批次:十個任務,九個過

## 這份文件為什麼存在,以及它記的第一件事

`02_Task_Queue/` 在 `.gitignore` 裡。十個任務包的 `feedback.md` 只活在這台機器上,
而核可判定是這批工作唯一的結論 —— 不落進版控就是漂走。

**核可方式必須先說清楚:使用者於 2026-08-08 明示授權單軌核可(「我授權你可以核可自己」)。**

**這不是 C.A.S.E. §1 的雙軌核可。** 做這批工作的 session 就是核可它的 session。
未來讀到九個 `DONE` 的人不該把它讀成「協定跑通了」—— 協定的雙軌要求沒有被滿足,
是被授權繞過的。授權的理由是佇列從 2026-08-06 起全數卡在 `REVIEW`,
而沒有任何核可 session 跑過,佇列不會自己前進。

守衛層面的補充:`task-queue-guard.ts` 的 self-approval 規則靠 `startedHere` 這個
**當前 session 的記憶體集合**判斷,而且跑在 Pi 裡。這十個任務不是這個 session 移到
`IN_PROGRESS` 的,守衛不會響。**所以這次授權繞過的是協定,不是守衛。**

## 判定

| 任務 | 判定 | 決定性的一點 |
|---|---|---|
| Task_001_queue_advancer | DONE | DoD 九項全過、5/5 破壞被抓到;**但設計後來被證明有兩處錯誤**(見下) |
| Task_002_advancer_measurement | DONE | 遵循率 0/3 如實記,量測腳本自身的 glob 缺陷寫在結論旁邊 |
| Task_003_cwd_confusion | **REVIEW(不核可)** | 三項 DoD 未達成,見 [task-003-cwd-confusion.md](task-003-cwd-confusion.md) |
| Task_004_case_guard_bash | DONE | 5/5 破壞;後由 Task_008 實測證實:21 次 status 寫入 `bash` 0 次 |
| Task_005_research_depth_bash | DONE | 5/5 破壞;規劃復盤在動工前擋掉「scratch 也計分」這個會弱化守衛的做法 |
| Task_008_advancer_verdict | DONE | 量測腳本被自己的可證偽檢查抓到兩次,兩次都會讓主指標反過來 |
| Task_010_blocked_claim_vocabulary | DONE | 5/5 破壞;真正價值是它發現守衛從未響過,量出被擋呼叫的事件序列 |
| Task_011_blocked_claim_channel | DONE(附缺件) | 真實 session 交付證明成立;**`planning.md` 從未寫過,且不補寫** |
| Task_015_advancer_settled_loop | DONE | 八項 DoD 七項達成,第一項**以證據反轉**;3 分 14 秒走到 `REVIEW`,零升級 |
| Task_016_phase_tool_gate | DONE | 十一項十項當場達成,最後一項在 Task_015 落地後於同一條鏈上達成 |

## 三件核可過程本身查出來的事

### 一、八份 DoD 都寫了「安裝一致」,而在今天之前沒有工具能驗它

`Task_003` 結案時安裝版 `yes-hooks-bridge` 連 `harness-root.ts` 都沒有 —— 那一項 DoD 是假的。
其餘七份靠人手動 `diff` 記得,這次沒記得。

**一般化的教訓:DoD 條目若沒有對應的可執行檢查,它量的是寫的人當天記不記得。**
機制已於同日建成(`scripts/verify-bridges.py` 的 repo↔installed 漂移檢查)。

### 二、Task_001 的 DoD 九項全過,而它的設計是錯的

停滯以「注入次數」判定、放棄時去改任務的 `status.txt` —— 兩者都由 Task_015 推翻。
**這不是 Worker 沒做到 DoD,是 DoD 沒有問「這個判準對不對」。**
DoD 檢查的是「做到了沒有」,沒有一格在問「做的這件事對不對」。

### 三、協定沒有「產出已證實、前置文件缺失」這一格

`Task_011` 的交付有真實 session JSONL 為憑(模型收到注入後自己查檔並對使用者更正),
而 `planning.md` 從未寫過。

**選擇不補寫。** 事後補一份計畫是編造 —— 計畫的價值在動工之前,追認只讓紀錄看起來合規。
如實記為缺件。

以上三點皆列為 `Task_014_case_upstream_round2` 的上游輸入。

## 一句話

**授權我核可自己,不是授權我蓋章。**
唯一被擋下的那一項,是我自己漏掉、又由我自己核可的那一項 —— 那正是最該擋的組合。
