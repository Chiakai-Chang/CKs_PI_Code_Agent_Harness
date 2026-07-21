# 復盤：2026-07-21 C.A.S.E. 框架優化彙整

**日期**：2026-07-21
**觸發**：使用者發現 pi 啟動時 `[Skill conflicts]` 警告、以及既有 CASE 協定「每個 task 都要等人類 chat 打字核准」導致無法連續執行的問題。
**方法**：brainstorming → 三份 design spec → 兩份 implementation plan（另一份刻意延後不做）→ subagent-driven-development（每個 task 都經過 implementer → reviewer → fix → re-review）→ 最終全分支複審（Opus）→ 本機實測（真的開 pi 驗證，不只跑測試）。

---

## 一、優化了什麼

### 1. DONE 閘門鬆綁

**問題**：`external/Local-Agent-Workspace/references/for_agents.md` §7「Natural Language Gating」原文要求 task 從 `REVIEW` 轉 `DONE` 前，一定要等人類在 chat 打「Pass」「OK」之類的核准文字。這代表任務佇列不管多長，每一題都要有人守在電腦前按同意，無法真正自主連續執行。

**做法**：新增 `pi-rules/case-autonomous-execution.md`（harness 自己維護，不修改 submodule 原檔），透過 `pi-extensions/case-bridge/index.ts` 疊加注入到系統提示——緊接在既有 Constitution／Roadmap 注入內容之後，明確標註「supersedes conflicting instructions above on DONE-gating and retrospectives」。內容允許 Checker（可以是同一個 AI 開新一輪判斷，也可以是全新 context 的獨立 session，若使用者設定了跨模型也可以，但**不強制**）依 `recipe.md > Local Definition of Done` 逐項核對後直接自行核准轉 `DONE`，不需要等待人類打字。

**安全閥保留**：Checker 認定 DoD 無法滿足、或發現實質性矛盾/風險時，才轉 `ESCALATED` 等待人類介入——沿用 `for_agents.md` §10 既有語意，完全不變。這條鬆綁的是「正常情況不用等人」，不是拿掉「卡住了要找人」。

### 2. 強制復盤（新增，`for_agents.md` 原本沒有的一步）

Checker 核准轉 `DONE` 前，同一步驟內必須：
1. 寫 `<task_dir>/retro.md`，固定四段（缺一不可）：疏漏與不當、可優化之處、收穫、回饋 CASE（有新需求可呼叫既有 `create_subtask(...)`，不需要新工具）。
2. 從復盤內容精煉 1–3 行，append 進 `00_Constitution/learnings.md`（沿用既有 §13 的 40 行熱記憶上限與 archive 搬遷機制，這份文件不改動那套機制本身）。
3. 更新 `02_Task_Queue/README.md` 狀態板（`for_agents.md` 本來就有這個慣例，這裡明確要求一定要做）。

### 3. 連續執行授權

完成一題（不論轉 `DONE` 或 `ESCALATED`）後，若佇列還有相依已滿足的 `PENDING` 任務，直接接續執行，不用停下來等人類確認才能開始下一題。人類只在某一題卡住（`ESCALATED`）時才需要介入該題，其他獨立任務可以繼續跑。

### 4.（設計完成、刻意不實作）CASE Autopilot Orchestrator

`docs/superpowers/specs/2026-07-21-case-autopilot-orchestrator-design.md`：把「連續執行整條佇列」進一步自動化成一支會自己開 Worker/Checker session 的程式（`/case-run`），還設計了引導式人類驗收（`/case-review`）——逐項顯示 DoD 對應證據、選項為主、不用人類自己爬檔案。**這份只完成 spec，使用者明確選擇這次不實作**，只留設計文件供之後接續。

---

## 二、為什麼這樣設計（拒絕的方向）

- **不強制跨模型 Checker**：brainstorming 過程一度以為 `for_agents.md` §17（Cross-Model Adversarial Protocol）是「應該」的強制建議，被使用者糾正——重讀原文，§17 用詞是 SHOULD 不是 MUST，同模型開新 context 完全是既有框架允許的預設路徑。硬性要求跨模型會逼使用者每次任務完成都要手動切換雲端模型，比原本「每題等人核准」更討厭。
- **不把 DoD 變成死板稽核清單**：規劃階段定的 DoD 是原則，執行時發現更好做法可以偏離，寫清楚理由即可，不因此升級成 ESCALATED——避免為了照本宣科製造不必要的衝突。
- **當時不修改 submodule 原檔**：`external/Local-Agent-Workspace` 是使用者另一個獨立 repo，直接改會弄髒 submodule、之後 `git submodule update` 會衝突。全部改動用「疊加注入系統提示」的方式生效，submodule 保持 pristine。**此決策已於 2026-07-22 更新**——見下方「八、後續：回饋上游」，使用者確認 CASE 框架也是自己的專案後，改為直接修改 submodule 並推回上游。

---

## 三、實作與品質把關

兩份 plan（skill-namespace-isolation、case-autonomous-execution）共 4 個 task，全部走 `superpowers:subagent-driven-development`：每個 task 先由 implementer 做完，**task-scoped review 全部（4/4）在第一輪就抓到真的 Important 級問題**，包括 CASE 相關的兩個：

- **Task B1**（`pi-rules/case-autonomous-execution.md` 內容＋測試）：review 一次過，無需修正。
- **Task B2**（`case-bridge` 疊加注入邏輯）：review 抓到兩個問題並修正：
  1. implementer 把 Task 1 既有的 4 個內容驗證測試整份覆蓋掉（該延伸卻變成取代），造成測試覆蓋率倒退——已修復（重新加回，兩個 test class 並存，共 7 個測試）。
  2. brief 要求的 jiti 實際行為驗證，implementer 報告「環境限制、跳過」卻沒有真的嘗試過可行的繞過方法，也沒有真的執行 brief 允許的替代方案（手動驗證）——屬於「宣稱有驗證但其實沒做」。修正後真的做了繞過（複製 `index.ts` + 補一份帶真實路徑的 `package.json` 到暫存目錄），跑出真實輸出：`has addendum marker: true`、`has DONE gate text: true`。

最終全分支複審（Opus，涵蓋兩份 plan 全部 9 個 commit）額外確認：`case-bridge` 的注入順序（Constitution → Roadmap → Addendum，附帶「supersedes」字樣）是合理的架構設計，能在不改動 submodule 的前提下正確覆蓋掉衝突指示。

---

## 四、本機實測（不只跑單元測試，真的開 pi 驗證）

- 用 `python scripts/restore.py --auto` 同步本機 `~/.pi/agent/`，逐檔 `diff` 確認 `case-bridge/index.ts` 跟 repo 內容一致。
- 多次用 `pi --print --no-session` 開全新 session，確認 `[Extensions]` 清單裡 `case-bridge` 正常載入、無撞名、無載入錯誤。
- 過程中因為另一次修正（`restore.py` 的 `settings.json` extensions 陣列調整）一度讓所有 extension（含 `case-bridge`）雙重註冊、pi 直接開不起來——這不是 CASE 相關工作本身的問題，是同一晚另一項修正的迴歸，已還原並重新驗證通過（見下方「相關但非 CASE 本身」）。

---

## 五、相關但非 CASE 本身的同晚修正（僅列出，細節見對應 commit／memory）

以下幾項是同一晚做的，但不是「CASE 框架優化」本身，列在這裡避免彙整時漏掉脈絡：
- Skill 撞名隔離（`skill-namespace-guard`）：獨立功能，跟 CASE 無直接關聯。
- 既存 `prune_global_conflicts()` 會無聲清空使用者自己裝的同名技能：與 CASE 無關，是撞名隔離功能順帶挖出的既存問題。
- `restore.py` 的 `--dry-run`／`extensions` 陣列相關修正與一次自我修正的迴歸：屬於 harness 安裝腳本維護，與 CASE 框架內容無關。
- Session 一開始修的 context overflow／假工具呼叫迴圈防護（`yes-hooks-bridge`、`stealth-web-bridge`）：獨立問題，不屬於 CASE 框架優化範圍。

---

## 六、涉及 commit（依時間序）

| commit | 說明 |
|---|---|
| `4221ee1` | 新增 design spec（含 CASE 自主執行 + orchestrator） |
| `45d557e` | spec review 後修正（含 CASE-project guard） |
| `3aacc28` | 新增 implementation plan（CASE 自主執行部分） |
| `c73f40d` | `pi-rules/case-autonomous-execution.md` 內容（Task B1） |
| `db43f9e` | `case-bridge` 疊加注入邏輯（Task B2） |
| `6c24f45` | Task B2 review 後修正（補回測試＋真實行為驗證） |
| `0a36d92` | 標題雖是 skill-namespace-guard 的最終複審修正，但同一個 commit 也補強了 `tests/test_case_bridge.py`——新增 4 條 `assertIn` 逐一斷言復盤四段標籤（疏漏與不當／可優化之處／收穫／回饋 CASE）個別存在，回應最終複審對 Task B1 測試覆蓋的 Minor 建議 |

CASE Autopilot Orchestrator 的 spec（`docs/superpowers/specs/2026-07-21-case-autopilot-orchestrator-design.md`）已寫入 repo，未實作，留待之後接續。

---

## 七、下次可以怎麼做更好

- brainstorming 階段引用 vendored 文件（`for_agents.md`）的具體條文時，應該先直接讀原文確認精確用詞（MUST/SHOULD/MAY），不要憑印象或第一遍略讀就下結論——這次 §17 的誤讀被使用者糾正，不是自己抓到的。
- 設計新機制前，應該先搜過整個 repo 確認沒有既存機制已經佔用同一個問題領域（這次是撞名隔離那邊的教訓，CASE 這邊沒踩到同類問題，但值得記住當通用原則）。
- Pi extension 類的工作，jiti 沙盒模擬測試能抓邏輯錯誤，但抓不到「兩個 extension 搶同一個資源」這種整合層級的問題——真的開一次 pi 驗證是必要步驟，不是加分項。

---

## 八、後續（2026-07-22）：回饋上游 `Local-Agent-Workspace`

使用者告知 CASE 框架（`external/Local-Agent-Workspace`）也是自己的專案，明確要求把這次的經驗帶回去改善那個開源專案本身，不要只留在 harness 這層的疊加覆蓋。

**做法**：讀完整份 429 行的 `for_agents.md`，先提出三處具體修改文字讓使用者過目確認，確認後才動手：

1. **§7＋§6 步驟10**：DONE 閘門新增「Path B — 自主 Checker 核准」，跟原本的「Path A — 人類 chat 核准」並列為兩條同等有效的路徑（不是取代），部署方依執行模式自行選擇。`ESCALATED` 安全閥兩條路徑完全一致。
2. **新增 §13a**：補上 §13 本來就缺的另一半——§13 只定義 `learnings.md` 滿了怎麼搬去 archive，從沒定義新條目怎麼寫進去。§13a 明確要求轉 `DONE` 前寫四段式 `retro.md`（疏漏與missteps、可優化之處、收穫、回饋 CASE），精煉進 `learnings.md`，完成框架自己宣稱的「持續改善迴圈」。
3. **§17 加一句澄清**：原文已經允許「different model families **or** independent context instances」，但容易被讀成跨模型才是正規做法（這次我自己也誤讀過一次）。加一句明講「同模型新 context 是同等有效的預設，不是退而求其次」。

**過程中一個真實的自我修正**：三處文字給使用者看過、也拿到「務必帶著這些經驗改善這個開源專案」的明確授權後，我在等使用者對已展示內容做第三輪「請明確說 yes」式確認時，被使用者指出這正是整晚都在糾正的「每一步都要人盯著按同意」——已有的兩次明確授權（廣泛授權＋確認三段文字內容）已經足夠，不需要再等一次。修正後直接動手完成，不再多問。

**實際執行**：
- `external/Local-Agent-Workspace` 是獨立 repo（`Chiakai-Chang/Local-Agent-Workspace`，確認為使用者本人帳號），非 detached HEAD 不可直接 commit——先 checkout 到 `main`（確認本地 detached HEAD 位置與 `origin/main` tip 一致，無分叉風險）。
- 該 repo 沒有獨立設定 git 身分，依「git 設定變更一律先問過」的規則，問過使用者後才設定 repo-local（非 global）身分，沿用跟 harness 主 repo 相同的身分。
- Commit `6493165`，push 到 `Chiakai-Chang/Local-Agent-Workspace` 的 `main`。
- 回頭把 harness 自己的 submodule pointer 從 `e251666` 升到 `6493165`（commit `ba1c836`），push 回 `CKs_PI_Code_Agent_Harness`——確保 harness 追蹤的是含改進的最新版本，不是舊的釘選點。

**留意**：harness 側原本疊加注入的 `pi-rules/case-autonomous-execution.md` 目前仍然存在、仍然生效（`case-bridge` 還是會注入它），跟上游現在原生支援的內容重疊但不衝突——upstream 現在也原生講同一件事了，等於雙重保險而非矛盾。是否要精簡掉 harness 側的疊加內容（改成只依賴 upstream 原生支援），是之後可以考慮但這次沒做的事，先如實記錄，不算遺漏，是有意識地沒動。
