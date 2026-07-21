# CASE Autopilot Orchestrator 設計 (2026-07-21)

> 依賴 `2026-07-21-case-autonomous-execution-design.md` 定義的協定文字先存在（DONE 閘門鬆綁 + 強制復盤步驟）。本篇是把「連續執行整個 task queue」進一步自動化成一支會自己開 Worker/Checker session 的程式，屬於錦上添花的加強，不是必要前提——協定文字本身在任何手動走 task queue 的互動式 session 就已經生效。

## 目標 (Goal)
一個指令跑完整個可執行的 task queue，不需要人類在旁邊逐題確認，只在真正 ESCALATED 時停下等人類。人類真的需要出手時（ESCALATED，或想主動抽查任何一題），AI 要一步一步、逐項引導著看該看什麼、給選項讓人選，不是丟一堆原始文字要人類自己爬、自己手動改 status.txt。

## 非目標 (Non-Goals)
- 不強制跨模型（同上一篇），Checker 預設沿用同一顆模型、乾淨新 context；跨模型只在使用者設定 `caseAutopilot.checkerModel` 時才啟用。
- 不做 CI/CD 整合、不做跨機器分散式任務排程。
- 不取代人類在 ESCALATED 時的介入——那部分行為完全不變，只是把「怎麼介入」變得好用。
- 引導式驗收（Component D）不要求 `/case-run` orchestrator 一定要在跑——單獨一支指令，任何互動式 session 都能用。

## 架構與元件

### 新 extension `pi-extensions/case-autopilot-bridge/index.ts`
註冊指令 `/case-run [task_id?]`：
1. 掃 `02_Task_Queue/`，找 `status.txt = PENDING` 且相依任務已 `DONE` 的 task。
2. 用 Pi SDK（`import { createAgentSession } from "@earendil-works/pi-coding-agent"`）開一個 **Worker 子 session**：`createAgentSession({ cwd: taskDir, model })`，系統提示注入 `role.md`+`recipe.md`，跑到它呼叫 `submit_for_review`（狀態轉 REVIEW）或卡住為止。
3. Worker 完成後，開一個**全新、獨立 context 的 Checker 子 session**（`model` 預設沿用同一顆；若設定 `caseAutopilot.checkerModel`，才改用該設定），餵給它 `recipe.md > Local DoD` + `output.md`，讓它核對並執行前一篇 B 段的復盤步驟（寫 `retro.md`、精煉進 `learnings.md`、更新 README 狀態板）。
4. 依 Checker 結果轉 `DONE`／退回 `PENDING`（重試計數 <3）／`ESCALATED`（重試 ≥3 或 Checker 認定無法核准）。
5. 該題結束後，若非 ESCALATED，自動抓下一個符合條件的 PENDING 任務重複 2–4；佇列清空或該次執行遇到 ESCALATED 才停止該題的迴圈（其他獨立、無依賴關係的任務可以繼續跑）。
6. 安全閥：`--max-tasks`（預設 10）與 `--timeout-per-task`（預設 30 分鐘）兩個上限，避免真的失控狂跑或卡死不動——呼應稍早假工具呼叫迴圈那次教訓，自動化迴圈一定要有硬上限，不能只靠模型自己判斷該停。
7. 該題轉 `ESCALATED` 時，用 `ctx.ui.confirm()` 主動問人類「Task_<NNN> 卡住了（<escalate 理由摘要>），要現在引導你看嗎？」——答應就直接呼叫 Component D 的引導流程，不用人類自己再去找、再打 `/case-review`。

### Component D — 引導式人類驗收（`/case-review <task_id>`）
同一支 extension 內新增指令，獨立於 orchestrator 之外也能單獨使用（人類想主動抽查任何一題，不管有沒有在跑 `/case-run`）。

**核心原則：一次只問一件事、用選項、AI 先幫忙指出證據在哪，不要求人類自己爬原始檔案或手打自由文字。**

1. **解析 DoD**：讀 `recipe.md > Local Definition of Done`，用既有的 markdown checklist 格式（`- [ ] item`）逐行拆成獨立項目。
2. **逐項引導**（每項一輪）：
   - 先顯示這項要驗什麼、AI 找到的相關證據指向哪（比對 DoD 項目文字關鍵字，從 `output.md`／`action_log.jsonl`／`retro.md` 挑出相關段落或檔案路徑，直接引用出來——這是「提示要看什麼」的核心，不是叫人類自己去找）。若 Worker 在 `retro.md`／`output.md` 已經記錄「這項有意偏離、理由是 X」（呼應 CASE 協定「DoD 是原則不是死板清單」），把偏離理由一併顯示在這裡，不要讓人類誤判成沒做。
   - 用 `ctx.ui.select()` 問，選項固定四個：`✅ 通過` / `❌ 有問題` / `🤔 不確定，等一下再看` / `⏭ 這項不適用（呼應已記錄的偏離理由）`。
   - 選「❌ 有問題」→ 用 `ctx.ui.input()` 追問「這項具體哪裡有問題？」，回覆與該 DoD 項目**綁在一起**存起來（不是丟進一團自由文字），確保之後產出的 `feedback.md` 是「第幾項 DoD → 具體意見」的結構化對應，不是一坨籠統抱怨。
   - 選「🤔 不確定」的項目記下來，全部項目跑完後再回頭問一次（給人類重新看一輪的機會，而非卡在同一項）。
3. **總結確認**：全部項目有結論後，用 `ctx.ui.select()` 顯示總結（「N 項通過／M 項有問題／K 項不適用」+ 有問題項目的簡短列表）並問「送出這個結果？」`[確認送出]` `[回頭改]`。
4. **依總結分派**：
   - 全部通過或不適用 → 轉 `DONE`（若這題原本是 ESCALATED，人類手動核准等同解除卡關，比照既有 §10「Human intervention」路徑），照 Component B 定義寫復盤三件套。
   - 有任一項「有問題」→ 把收集到的逐項意見組成結構化 `feedback.md`（沿用既有格式，每條意見標明對應第幾項 DoD），轉 `PENDING`（未達重試上限）或維持 `ESCALATED`（已達上限，等待人類決定 §10 的 Re-specify／Split task）。
5. **批次模式**：`/case-review` 跑完一題後，若還有其他待審（ESCALATED 或人類主動排進的清單），用 `ctx.ui.confirm()` 問「還有 N 題待審，要繼續下一題嗎？」，人類可以一口氣連續審完一批，不用每題重新打指令。
6. `action_log.jsonl` 記一筆 `role: "human"` 的 `change_status` 事件（區別於 Checker/AI 核准），保留「這題是人類親自看過核准的」可追溯性。

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
      → 不過，重試 ≥3 或無法核准 → 轉 ESCALATED
             → ctx.ui.confirm() 問人類要不要現在引導審查
                 → 是 → Component D 引導流程 → 通過 DONE／有問題 PENDING／維持 ESCALATED
                 → 否 → 該題迴圈停止，其餘任務可續跑，人類之後手動 /case-review 補審
  → 該題結束 → 檢查安全閥（max-tasks / timeout）→ 未觸頂 → 抓下一個 PENDING 任務，重複

/case-review <task_id>（獨立指令，不依賴 /case-run 是否在跑）
  → 解析 recipe.md 的 DoD checklist
  → 逐項：顯示證據 + retro.md 記錄的偏離理由 → ctx.ui.select() 四選項 → 「有問題」再 ctx.ui.input() 收集具體意見
  → 全部跑完 → 總結 → ctx.ui.select() 確認送出
  → 通過/不適用 → DONE + 復盤三件套；有問題 → 結構化 feedback.md → PENDING 或維持 ESCALATED
  → 還有其他待審 → ctx.ui.confirm() 問是否連續審下一題
```

## 錯誤處理
- `/case-run`／`/case-review` 在非 CASE 專案（cwd 沒有 `00_Constitution` 或 `02_Task_Queue`）被呼叫：立刻 `ctx.ui.notify` 說明「這不是 CASE 專案」並中止，不嘗試建立任何結構或猜測，避免在錯的目錄亂寫檔案。
- Worker／Checker 子 session 是用 Pi SDK `createAgentSession()` 開的一般 session，會照常自動載入全域安裝的 extension（含 `yes-hooks-bridge` 的破壞性指令/目錄越界/迴圈三個 guard）——tonight 稍早修的安全網對子 session 一樣生效，不需要額外接線。
- Orchestrator 中途被中斷（當機/手動停止）：狀態完全靠 `status.txt`（既有「File as State」原則，不變），重跑 `/case-run` 直接從目前狀態接續，沒有藏在記憶體裡的隱藏狀態。
- Checker session 本身出錯（例如呼叫失敗、逾時）：視為「不確定」，退回 `REVIEW`，記錄原因，計入既有 3 次重試上限，不能因為 Checker 掛掉就靜默轉 DONE。
- 觸發安全閥（`max-tasks`/`timeout`）：停止迴圈，印出目前佇列剩餘狀態，不視為錯誤，是預期的煞車機制。
- DoD checklist 解析失敗（`recipe.md` 格式跑掉、抓不到任何 `- [ ]` 項目）：`/case-review` 不能無聲跳過，要明確 `ctx.ui.notify` 告知「DoD 格式無法解析」並列出原始內容讓人類自己判斷，fail open 不 fail silent。
- 人類在引導流程中途取消（Esc / 關閉對話）：狀態維持在觸發 `/case-review` 前的原樣，已收集但尚未送出的逐項意見直接丟棄，不留半套髒狀態。

## 測試
- 佇列掃描/相依判斷抽成純函式，比照稍早 `stealth-web-bridge`/`yes-hooks-bridge` 的驗證方式——用 Pi 真正的 jiti loader 載入、餵假的 `createAgentSession`/`ctx` stub，跑過 Worker→Checker→DONE、Worker→Checker→PENDING 重試、達到 3 次轉 ESCALATED 三條路徑，不需要真的打 LLM。
- 安全閥（max-tasks/timeout）各寫一個測試確認迴圈確實在觸頂時停止。
- DoD checklist 解析函式：抽成純函式單獨測（正常格式、缺項目、格式跑掉三種輸入）。
- Component D 用假的 `ctx.ui.select`/`ctx.ui.input`/`ctx.ui.confirm`（回傳預先設好的固定序列，模擬人類依序選擇）跑過：全通過轉 DONE、有一項「有問題」轉 PENDING 且 `feedback.md` 內容確實對應到那一項、批次模式問「繼續下一題」正確串接第二個 task_id。
