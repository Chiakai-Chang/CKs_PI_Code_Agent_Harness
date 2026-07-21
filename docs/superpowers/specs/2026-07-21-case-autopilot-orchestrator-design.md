# CASE Autopilot Orchestrator 設計 (2026-07-21)

> 依賴 `2026-07-21-case-autonomous-execution-design.md` 定義的協定文字先存在（DONE 閘門鬆綁 + 強制復盤步驟）。本篇是把「連續執行整個 task queue」進一步自動化成一支會自己開 Worker/Checker session 的程式，屬於錦上添花的加強，不是必要前提——協定文字本身在任何手動走 task queue 的互動式 session 就已經生效。

## 目標 (Goal)
一個指令跑完整個可執行的 task queue，不需要人類在旁邊逐題確認，只在真正 ESCALATED 時停下等人類。

## 非目標 (Non-Goals)
- 不強制跨模型（同上一篇），Checker 預設沿用同一顆模型、乾淨新 context；跨模型只在使用者設定 `caseAutopilot.checkerModel` 時才啟用。
- 不做 CI/CD 整合、不做跨機器分散式任務排程。
- 不取代人類在 ESCALATED 時的介入——那部分行為完全不變。

## 架構與元件

### 新 extension `pi-extensions/case-autopilot-bridge/index.ts`
註冊指令 `/case-run [task_id?]`：
1. 掃 `02_Task_Queue/`，找 `status.txt = PENDING` 且相依任務已 `DONE` 的 task。
2. 用 Pi SDK（`import { createAgentSession } from "@earendil-works/pi-coding-agent"`）開一個 **Worker 子 session**：`createAgentSession({ cwd: taskDir, model })`，系統提示注入 `role.md`+`recipe.md`，跑到它呼叫 `submit_for_review`（狀態轉 REVIEW）或卡住為止。
3. Worker 完成後，開一個**全新、獨立 context 的 Checker 子 session**（`model` 預設沿用同一顆；若設定 `caseAutopilot.checkerModel`，才改用該設定），餵給它 `recipe.md > Local DoD` + `output.md`，讓它核對並執行前一篇 B 段的復盤步驟（寫 `retro.md`、精煉進 `learnings.md`、更新 README 狀態板）。
4. 依 Checker 結果轉 `DONE`／退回 `PENDING`（重試計數 <3）／`ESCALATED`（重試 ≥3 或 Checker 認定無法核准）。
5. 該題結束後，若非 ESCALATED，自動抓下一個符合條件的 PENDING 任務重複 2–4；佇列清空或該次執行遇到 ESCALATED 才停止該題的迴圈（其他獨立、無依賴關係的任務可以繼續跑）。
6. 安全閥：`--max-tasks`（預設 10）與 `--timeout-per-task`（預設 30 分鐘）兩個上限，避免真的失控狂跑或卡死不動——呼應稍早假工具呼叫迴圈那次教訓，自動化迴圈一定要有硬上限，不能只靠模型自己判斷該停。

## 資料流
```
/case-run
  → 掃 02_Task_Queue，取下一個可執行 PENDING
  → 開 Worker session（cwd=task 目錄）
      → 走既有 §6 Worker Protocol（含自己的 3 次自癒重試，不變）
      → 轉 REVIEW
  → 開 Checker session（全新 context，同模型或設定的跨模型）
      → 對照 Local DoD 逐條檢查 output.md
      → 過 → 寫 retro.md → 精煉進 learnings.md → 更新 README 狀態板 → 轉 DONE
      → 不過，重試 <3 → 寫 feedback.md → 轉 PENDING（回 Worker）
      → 不過，重試 ≥3 或無法核准 → 轉 ESCALATED，該題迴圈停止，其餘任務可續跑
  → 該題結束 → 檢查安全閥（max-tasks / timeout）→ 未觸頂 → 抓下一個 PENDING 任務，重複
```

## 錯誤處理
- Orchestrator 中途被中斷（當機/手動停止）：狀態完全靠 `status.txt`（既有「File as State」原則，不變），重跑 `/case-run` 直接從目前狀態接續，沒有藏在記憶體裡的隱藏狀態。
- Checker session 本身出錯（例如呼叫失敗、逾時）：視為「不確定」，退回 `REVIEW`，記錄原因，計入既有 3 次重試上限，不能因為 Checker 掛掉就靜默轉 DONE。
- 觸發安全閥（`max-tasks`/`timeout`）：停止迴圈，印出目前佇列剩餘狀態，不視為錯誤，是預期的煞車機制。

## 測試
- 佇列掃描/相依判斷抽成純函式，比照稍早 `stealth-web-bridge`/`yes-hooks-bridge` 的驗證方式——用 Pi 真正的 jiti loader 載入、餵假的 `createAgentSession`/`ctx` stub，跑過 Worker→Checker→DONE、Worker→Checker→PENDING 重試、達到 3 次轉 ESCALATED 三條路徑，不需要真的打 LLM。
- 安全閥（max-tasks/timeout）各寫一個測試確認迴圈確實在觸頂時停止。
