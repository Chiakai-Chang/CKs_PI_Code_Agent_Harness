# CASE 自主執行協定 + 強制復盤 設計 (2026-07-21)

> `external/Local-Agent-Workspace`（`references/for_agents.md`）目前把「task 從 REVIEW 轉 DONE」寫死綁在人類在 chat 打「Pass/OK」（§7 Natural Language Gating），導致每題都要人盯著按同意。同時完全沒有「task 完成前做全面復盤（缺漏/不當/可優化/收穫），沉澱成知識資產」這一步——§13 只處理 learnings.md 滿了要搬去 archive，沒定義內容從哪裡來。這兩個都是缺口，不是刻意設計。
>
> 本篇只涵蓋「協定文字」本身（Pi 系統提示層級的規則），適用於任何手動走 task queue 的 Pi session，不需要額外程式。真正把「連續執行多題」自動化成一支會自己開 session 的 orchestrator，是後續、依賴本篇協定文字存在的獨立子專案，見 `2026-07-21-case-autopilot-orchestrator-design.md`。

## 目標 (Goal)
移除「每題都要人類點頭」的阻塞，同時保留「Worker 不能自己批准自己」這個框架本來就有的核心安全性質。人類只在真正卡住（ESCALATED）時才需要出現。每個 task 完成前，強制做一次結構化復盤並寫入知識資產。

## 非目標 (Non-Goals)
- **不強制跨模型**。§17 Cross-Model Adversarial Protocol 本來就是 SHOULD，不是 MUST——同一顆模型、乾淨新 context 做 Checker 完全合法，是預設路徑。跨模型只在使用者手動設定時才啟用，絕不逼使用者切換模型。
- **不把 DoD 變成死板稽核清單**。DoD 是規劃階段定的原則，執行時發現更好做法可以偏離，寫清楚理由即可，不因此卡住升級成 ESCALATED。
- **不直接修改 `external/Local-Agent-Workspace` submodule**。它是使用者另一個獨立 repo（Chiakai-Chang/Local-Agent-Workspace）vendor 進來的，改了會弄髒 submodule、之後 `git submodule update` 會衝突。改動全部發生在 CKs_PI_Code_Agent_Harness 自己的檔案裡，用疊加注入的方式生效。
- **不包含把連續執行自動化成程式的 orchestrator**——那是獨立子專案（見上方連結），本篇交付的協定文字本身就能立即用（任何互動式 Pi session 手動照著走），不依賴 orchestrator 存在。

## 架構與元件

### A. 新增 `pi-rules/case-autonomous-execution.md`（harness 自己的補充協定）
純文字，透過 `pi-extensions/case-bridge/index.ts` 既有的 `before_agent_start` handler 疊加注入到 system prompt，緊接在既有的 Constitution/Roadmap 內容之後（不修改 for_agents.md 本身，是疊加，不是覆蓋；`case-bridge` 只需追加一段讀檔+拼接邏輯，複用它已有的 `readHead`/`isCaseProject` helper）。內容明確覆寫/補充三處：
1. **鬆綁 §7 DONE 閘門**：Checker（AI，同模型新 context 或設定的跨模型皆可）可以直接依 `recipe.md > Local Definition of Done` 逐條核對 `output.md` 後自行核准轉 DONE，不必等待人類在 chat 回覆「Pass/OK」。人類只在 Checker 認定 DoD 無法滿足、或發現矛盾/風險時才需要介入（沿用既有 `ESCALATED` 狀態，語意不變）。
2. **新增強制復盤步驟**（見下方 B）。
3. **明確授權連續執行**：完成一題（無論 DONE 或該題 ESCALATED）後，若佇列還有依賴已滿足的 PENDING 任務，直接接續下一題，不用停下來等待人類確認才能開始下一題。

### B. 復盤步驟定義（新增在補充協定文件內）
Task 轉 DONE 之前（Checker 核准的同一步驟內）必須：
1. 寫 `<task_dir>/retro.md`：固定四段——「這次過程有沒有疏漏或不當之處」「有沒有可優化的地方」「這次的收穫/學到什麼」「有沒有發現新需求該回饋進 CASE（若有，呼叫既有 `create_subtask` 建新任務，不用新工具）」。
2. 從 `retro.md` 精煉出 1–3 行濃縮條目，append 進 `00_Constitution/learnings.md`（沿用既有 §13 的 40 行熱記憶上限與 archive 搬遷機制，完全不改）。
3. 更新 `02_Task_Queue/README.md` 的狀態板（既有慣例，明確寫進協定，不再只是隱含）。

## 資料流
```
Worker 完成 task（既有 §6，含 3 次自癒重試，不變）→ REVIEW
  → Checker（同 session 新一輪判斷，或另開 session）依 Local DoD 逐條核對 output.md
      → 過 → 寫 retro.md → 精煉進 learnings.md → 更新 README 狀態板 → 轉 DONE
             → 佇列還有可執行 PENDING → 直接接續，不停下等人類
      → 不過，重試 <3 → 寫 feedback.md → 轉 PENDING（回 Worker 修正）
      → 不過，重試 ≥3 或發現矛盾/風險 → 轉 ESCALATED，等待人類介入
```

## 錯誤處理
- Checker 判斷不確定（DoD 條件本身模糊、無法客觀核對）：不得默認通過，視同「不過」處理，走重試/ESCALATED 路徑，理由寫進 `feedback.md`。
- 狀態完全靠 `status.txt`（既有「File as State」原則），協定文字本身不引入任何額外的隱藏狀態。

## 測試
- `case-bridge` 的 contract test（比照既有風格）：斷言 `pi-rules/case-autonomous-execution.md` 存在，且其內容被 `before_agent_start` 回傳的 systemPrompt 疊加進去（在有 `00_Constitution` 的專案下）。
- 人工驗收：在一個測試用 CASE 專案的 task folder 手動走一輪（Worker 完成 → 同 session 轉 Checker 角色核對 DoD → 應該不再要求輸入「Pass」文字才轉 DONE），確認 `retro.md`/`learnings.md`/README 狀態板三個產出都確實被寫入。
