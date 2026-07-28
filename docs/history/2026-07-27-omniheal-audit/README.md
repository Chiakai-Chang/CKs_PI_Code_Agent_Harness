# 2026-07-27 OmniHeal 稽核產物（已封存）

這些檔案來自 commit `3317c75`（2026-07-27，"fix(harness): resolve infinite loop bugs, audit via OmniHeal"）——
也就是 pi 在健檢過程中卡死的那一次工作階段所留下的規劃與快照。

**為何從專案根目錄移到這裡**：`planning-with-files-bridge` 以**根目錄是否存在 `task_plan.md`** 判定「有進行中的計畫」，
存在就在**每一輪**把內容注入 system prompt。實測該注入為 **3,015 字元（約 750 tokens）**，內容是一份早已完成／中止的
任務佇列（「緊急除錯：無限迴圈」等）。也就是說，每次對話都在告訴模型有個過時的任務正在進行中——這正是啟動畫面上
`[planning-with-files] active plan detected` 的來源。

`summary.md` 另宣稱「176 / 176 測試通過」，該數字早已過時。

檔案保留於此僅供歷史查閱，不再參與任何注入。當時那次稽核真正的成果與後續完整根因，記錄於
[docs/retro/](../../retro/) 下 2026-07-27 與 2026-07-28 的兩份復盤。

> 要重新啟用計畫模式，在專案根目錄建立新的 `task_plan.md` 即可——bridge 會自動偵測。
