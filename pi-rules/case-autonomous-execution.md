# CASE 自主執行補充協定 (Harness Addendum)

> 本文件補充（不取代）`external/Local-Agent-Workspace/references/for_agents.md`
> 的 Worker/Checker 協定。與該檔案衝突之處，以本文件為準。

## 1. DONE 閘門鬆綁

`for_agents.md` §7「Natural Language Gating」原文要求 DONE 轉換必須等待
人類在 chat 中以自然語言核准（例如「Pass」「looks good」）。此規則放寬如下：

- Checker（可以是同一個 AI 在同一個 session 開新一輪判斷，也可以是全新
  context 的獨立 session；若使用者設定了不同模型也可以是跨模型，但不
  強制）在**依 `recipe.md > Local Definition of Done` 逐項核對
  `output.md` 後**，可以直接自行核准並將 `status.txt` 轉為 `DONE`，
  不需要等待人類在 chat 中輸入任何核准文字。
- DoD 是規劃階段訂下的原則，不是死板稽核清單。執行過程中若發現更好的
  做法而偏離 DoD 條文，只要在 `output.md` 或 `retro.md` 中清楚記錄偏離
  的理由，Checker 可以將該項目視為滿足，不需要因為字面不符而卡住。
- Checker 認定 DoD 無法滿足、或發現實質性矛盾/風險時，才轉 `ESCALATED`
  等待人類介入——這條沿用 `for_agents.md` §10 既有語意，完全不變。

## 2. 強制復盤（每個 task 轉 DONE 之前必做）

在 Checker 核准轉 `DONE` 的**同一個步驟內**，必須依序完成：

1. 寫 `<task_dir>/retro.md`，固定四段（缺一不可）：
   - **疏漏與不當**：這次過程有沒有遺漏或做得不恰當的地方？
   - **可優化之處**：有沒有更好的做法，下次可以怎麼改進？
   - **收穫**：這次任務學到了什麼、有什麼值得記住的經驗？
   - **回饋 CASE**：有沒有發現新的需求或缺口該補進任務佇列？若有，
     呼叫既有的 `create_subtask(...)` 建立新任務（不需要新工具）。
2. 從 `retro.md` 的「收穫」與「可優化之處」兩段，精煉出 1–3 行的濃縮
   條目，append 進 `00_Constitution/learnings.md`（沿用 `for_agents.md`
   §13 既有的 40 行熱記憶上限與 archive 搬遷機制，此文件不改動那套
   機制本身）。
3. 更新 `02_Task_Queue/README.md` 的狀態板，把這個 task 的欄位改成
   目前狀態（`for_agents.md` 原本就有這個慣例，這裡明確要求一定要做，
   不能省略）。

## 3. 連續執行授權

完成一題（不論轉 `DONE` 或該題轉 `ESCALATED`）之後，若任務佇列中還有
相依任務已 `DONE`、狀態為 `PENDING` 的其他任務，**直接接續執行下一題**，
不需要停下來等待人類確認才能開始。人類只在某一題被轉為 `ESCALATED`
時才需要介入該題；其他獨立、不相依於該卡住任務的其他任務，可以繼續
自主執行。

## 4. 執行前計畫自我復盤（`for_agents.md` §6 步驟 4 補強）

`role.md` 與 `recipe.md`（Objective／Input Sources／Output Specification／
Local DoD／Constraints）對這個 task 而言，等同於 `00_Constitution/core.md`
對整個專案的地位——一樣是拘束性的「小憲法」，不是可以自由詮釋的參考資料。

Worker 在讀完 recipe 之後、**動任何 input 或寫任何程式碼之前**，除了原本
就要寫的 `planning.md`（具體步驟、目標檔案、測試策略），必須在同一個檔案
裡加一段 `## Self-Review`，自問三件事：

1. `recipe.md > Local Definition of Done` 每一項，計畫裡有沒有對應的具體
   步驟去滿足它？
2. 計畫裡有沒有任何步驟，跟 recipe.md 的 Constraints 衝突？
3. 計畫有沒有任何一部分，是建立在 `recipe.md`／`role.md` 根本沒有提供
   依據的假設上？

只要上面任何一題發現真的有缺口或矛盾，比照既有的錯誤處理規則，當成
「Contradictory instructions」或「Insufficient input」升級（`escalate_issue`），
**在動手執行前就升級，不要等做完才發現**。自我復盤沒有過，不得進入
`recipe.md > Input Sources` 讀取或任何程式修改。

（此條已同步回饋upstream `external/Local-Agent-Workspace`，見該 repo
commit `d6c5594`——`for_agents.md` §6 步驟 4 與 §19.D 的 `planning.md`
範本現在原生就有這段，這裡的補強是確保 harness 自己注入的系統提示
一定會帶到這條，不依賴使用者是否另外載入了 `for_agents.md` 全文。）
