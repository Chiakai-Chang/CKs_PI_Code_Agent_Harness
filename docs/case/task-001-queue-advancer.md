# Task_001_queue_advancer — 結論與上游回饋

任務包在 `02_Task_Queue/Task_001_queue_advancer/`(gitignore),本檔是它的結論摘錄。
抽出來的原因:`session-report.py --unharvested` 在第一次真實使用時報「全部都有被引用」,
而這份 retro 的三條上游回饋當時**一個字都沒進版本控制** —— 唯一的「提及」出現在一段
session 逐字稿裡。

## 交付

`pi-extensions/case-bridge/queue-advancer.ts` —— `turn_end` 讀佇列狀態,查 C.A.S.E. 轉換表
得出下一步,注入並觸發下一輪。預設關閉、fail closed。

七列查表全部只看檔案存在性,每列標明 `for_agents.md` 出處。同一步連推 3 次無前進即升級。

## 破壞測試:5/5 被抓到,其中 2 條是補強後才有牙齒

| 原本為什麼沒牙齒 |
|---|
| 「兩個 `IN_PROGRESS` 不猜」的 fixture 沒有 PENDING 任務,拿掉守衛後仍落到 null —— 壞的與對的結果相同 |
| 「`REVIEW` 不自我核可」斷言 `session\|checker`,而改寫成「可以直接核可」的版本下一句仍有 "session" |

## 給 C.A.S.E. 上游的三條回饋(本檔存在的主要理由)

**一、`action_log.jsonl` 假設「執行者會自己記錄」。** 對非 Pi 的執行者不成立。協定已容許
`log.md` 作為「較弱模型」的替代,但真正的分類是**「執行環境有沒有自動軌跡」**,不是模型強弱。
建議把 §Task Package Schema 第 8 項的措辭從能力導向改為環境導向。

**二、`--strict` 抓到了缺 `action_log.jsonl`,預設模式不會。** 這正是加 `--strict` 的理由被
驗證的一刻:預設模式下這個任務會以「✅ VERIFICATION PASSED」通過,而它當時**沒有任何稽核
軌跡**。上游那十條 warning 裡,這一條的實務代價最高。

**三、`--queue` 檢查的正是這個框架存在的理由,卻只是可選旗標。** 單任務驗證看不到
「一次一件」;佇列層看得到。建議在 `SKILL.md` 的 Checker 流程裡把 `--queue` 列為必跑。

## 已知限制(未解)

**推進器看不到其他 bridge 的糾正。** `yes-hooks-bridge` 的 compaction-echo 與 blocked-claim
也在 `turn_end` 發訊息,擴充之間看不到彼此的回傳值。Task_002 的結論是「本次未觀察到」——
**那不是證明**。`session-report.py` 現在會統計「兩輪之間最多幾則注入」,讓它變成可累積的數字。

**最根本的限制沒有變**:注入的內容仍是文字,模型仍可不照做。改變的是失敗的形狀。
