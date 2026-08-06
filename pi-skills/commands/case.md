---
description: "以 C.A.S.E. 任務佇列開始一件多階段工作:沒有佇列就先建立,有佇列就接著做下一項。每輪只做一項,做完復盤才收掉。把使用者打在 /case 後面的文字當作這件工作的目標。"
---

使用者要用 **C.A.S.E.**(Context-Aware Scaffold Engine)的任務佇列來推進一件多階段工作。
把使用者打在 `/case` 後面的文字當作**這件工作的目標**。

這個指令存在的原因很直接:實測顯示模型即使看得到 `case-framework` 技能的完整描述,也不會自己
去用它(3 次量測 0 次載入)。所以入口做成確定性的 —— 使用者打了,它就發生。

## 步驟

### 1. 先看現在有沒有佇列

```bash
ls -d 02_Task_Queue 2>/dev/null || ls -d C.A.S.E._Framework/02_Task_Queue 2>/dev/null
```

**有佇列** → 跳到步驟 3。
**沒有** → 步驟 2。

### 2. 建立骨架(只有在使用者用 `/case` 明確要求時才做)

```bash
python "$PI_HARNESS_ROOT/external/Local-Agent-Workspace/scripts/bootstrap.py" .
```

這會建立 `00_Constitution/`、`01_Roadmap/`、`02_Task_Queue/` 與模板。
**不要在使用者沒要求時自動做這件事** —— 那會在別人的專案裡憑空長出三個資料夾。

建完之後讀 `$PI_HARNESS_ROOT/external/Local-Agent-Workspace/SKILL.md`,那是協定本體。

### 3. 把目標切成任務,一個任務一個資料夾

`02_Task_Queue/Task_<NNN>_<slug>/`,每個至少要有:

| 檔案 | 內容 |
|---|---|
| `status.txt` | `PENDING`(五個 token 之一) |
| `role.md` | 這個任務專屬的角色設定 |
| `recipe.md` | `## Objective` + `## Local Definition of Done`(驗收清單,每項要可驗證) |

**切分的粒度:一個任務是一輪能做完並交付的東西。** 如果一個任務需要三次搜尋、兩份報告、
一次重構,它是三個任務。

### 4. 一次做一項

1. 把該任務的 `status.txt` 改成 `IN_PROGRESS`
2. 寫 `planning.md`,含 `## Self-Review`(對照 `recipe.md` 檢查計畫)
3. 執行,產出寫進 `output.md`
4. 寫 `retro.md`,四個段落缺一不可:
   `## Gaps & Missteps` / `## Optimization Opportunities` / `## Lessons Learned` / `## Feedback to CASE`
5. 驗證:
   ```bash
   python "$PI_HARNESS_ROOT/external/Local-Agent-Workspace/verifiers/verify.py" 02_Task_Queue/Task_<NNN>_<slug> --strict
   ```
6. `status.txt` 改成 `REVIEW`

**下一項要等這一項收掉才開始。** 這是佇列存在的全部理由。

### 5. 佇列層檢查

```bash
python "$PI_HARNESS_ROOT/external/Local-Agent-Workspace/verifiers/verify.py" --queue 02_Task_Queue --strict
```

### 6. 有新發現就進佇列,不要塞進當前任務

執行途中發現的新工作**寫成新的 `Task_<NNN>`**,狀態 `PENDING`。把它塞進手上這一項,
就是回到「一輪做完全部」——那正是 C.A.S.E. 要避免的事。

## harness 會替你做的事(不用自己做)

* **`action_log.jsonl` 由 harness 自動寫入**,每一次工具呼叫一行。不要自己維護它。
* 以下違規會被**擋下**並附上理由,不是提醒:
  * 跳過中間狀態(如 `PENDING` 直接改 `DONE`)
  * 在已有任務 `IN_PROGRESS` 時開第二個
  * 開啟這個任務的同一個 session 又把它改成 `DONE`(Worker 不能自我核可)
  * `DONE` 之前沒有 `retro.md`
  * 寫進不是當前進行中的那個任務目錄

被擋下時**照理由做**,不要繞路。理由會指名是哪個任務、下一步該做什麼。
