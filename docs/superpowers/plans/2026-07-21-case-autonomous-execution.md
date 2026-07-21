# CASE 自主執行協定 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增一份 harness 自己的補充協定文件，鬆綁 CASE 框架「DONE 一定要等人類 chat 打字核准」的規則，並新增強制復盤步驟；透過 `case-bridge` 疊加注入到 system prompt，不修改 `external/Local-Agent-Workspace` submodule 本身。

**Architecture:** 純文字協定檔 `pi-rules/case-autonomous-execution.md`（本 repo 管理），由 `pi-extensions/case-bridge/index.ts` 既有的 `before_agent_start` handler 讀取並疊加到既有 Constitution/Roadmap 注入內容之後。

**Tech Stack:** TypeScript（Pi extension，既有 `case-bridge` 擴充）、Python `unittest`（contract test）。

## Global Constraints

- 不修改 `external/Local-Agent-Workspace` submodule 內任何檔案。
- 零依賴；測試用 `unittest`。
- 中文文件內容一律正體中文、臺灣慣用語（見本 repo `pi-rules/AGENTS.md` §0）。
- 不強制跨模型；不把 DoD 變成死板稽核清單。

## File Structure

- `pi-rules/case-autonomous-execution.md` — 新增，補充協定內容（DONE 閘門鬆綁、強制復盤、連續執行授權）。
- `pi-extensions/case-bridge/index.ts` — 修改，`before_agent_start` 內新增讀取並疊加此檔案。
- `tests/test_case_bridge.py` — 新增，contract test。

---

### Task 1: 撰寫補充協定內容 + 存在性/內容測試

**Files:**
- Create: `pi-rules/case-autonomous-execution.md`
- Create: `tests/test_case_bridge.py`

**Interfaces:**
- Produces: `pi-rules/case-autonomous-execution.md`（後續 Task 2 會讀取此檔案路徑）。

- [ ] **Step 1: 寫失敗測試**

新建 `tests/test_case_bridge.py`：

```python
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class TestCaseAutonomousExecutionAddendum(unittest.TestCase):
    ADDENDUM = "pi-rules/case-autonomous-execution.md"

    def test_addendum_file_exists_with_required_sections(self):
        c = read(self.ADDENDUM)
        self.assertIn("DONE 閘門鬆綁", c)
        self.assertIn("強制復盤", c)
        self.assertIn("連續執行授權", c)
        self.assertIn("retro.md", c)
        self.assertIn("learnings.md", c)
        self.assertIn("create_subtask", c)

    def test_addendum_does_not_require_human_chat_approval(self):
        c = read(self.ADDENDUM)
        self.assertIn("不需要等待人類在 chat 中", c)

    def test_addendum_does_not_force_cross_model(self):
        c = read(self.ADDENDUM)
        # 必須明確允許同模型新 context，不能只有跨模型選項
        self.assertIn("同一個 AI", c)

    def test_addendum_preserves_escalation_semantics(self):
        c = read(self.ADDENDUM)
        self.assertIn("ESCALATED", c)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python -m unittest tests.test_case_bridge -v`
Expected: FAIL — `FileNotFoundError`（`pi-rules/case-autonomous-execution.md` 還不存在）

- [ ] **Step 3: 撰寫補充協定內容**

新建 `pi-rules/case-autonomous-execution.md`：

```markdown
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
```

- [ ] **Step 4: 執行測試確認通過**

Run: `python -m unittest tests.test_case_bridge -v`
Expected: `TestCaseAutonomousExecutionAddendum` 4 個測試全部 PASS（`TestCaseBridgeInjectsAddendum` 尚未寫，Task 2 才會有）

- [ ] **Step 5: Commit**

```bash
git add pi-rules/case-autonomous-execution.md tests/test_case_bridge.py
git commit -m "feat(case): add autonomous-execution protocol addendum"
```

---

### Task 2: `case-bridge` 疊加注入補充協定

**Files:**
- Modify: `pi-extensions/case-bridge/index.ts`
- Test: `tests/test_case_bridge.py`（延伸）

**Interfaces:**
- Consumes: `pi-rules/case-autonomous-execution.md`（Task 1 產出，路徑固定）。
- Consumes（既有，不變）：`case-bridge/index.ts` 現有的 `readHead(dir, name, maxChars)`、`isCaseProject(cwd)`、`HARNESS_ROOT` 解析邏輯。

- [ ] **Step 1: 寫失敗測試**

在 `tests/test_case_bridge.py` 新增一個 class：

```python
class TestCaseBridgeInjectsAddendum(unittest.TestCase):
    IDX = "pi-extensions/case-bridge/index.ts"

    def test_reads_addendum_from_pi_rules(self):
        c = read(self.IDX)
        self.assertIn('"pi-rules"', c)
        self.assertIn('"case-autonomous-execution.md"', c)

    def test_injects_addendum_with_marker(self):
        c = read(self.IDX)
        self.assertIn("BEGIN C.A.S.E. HARNESS ADDENDUM", c)
        self.assertIn("END C.A.S.E. HARNESS ADDENDUM", c)

    def test_addendum_only_injected_for_case_projects(self):
        c = read(self.IDX)
        # 疊加邏輯必須在 isCaseProject(ctx.cwd) 的 if 區塊內，
        # 用既有 constitution/roadmap 注入區塊做參照點：
        # BEGIN 標記必須出現在 "if (isCaseProject(ctx.cwd))" 之後。
        idx_if = c.index("if (isCaseProject(ctx.cwd))")
        idx_marker = c.index("BEGIN C.A.S.E. HARNESS ADDENDUM")
        self.assertGreater(idx_marker, idx_if)
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python -m unittest tests.test_case_bridge -v`
Expected: FAIL — 3 個新測試失敗（`case-bridge/index.ts` 還沒有這些字串）

- [ ] **Step 3: 修改 `case-bridge/index.ts`**

在既有 `if (isCaseProject(ctx.cwd)) { ... }` 區塊內，`roadmap` 那段後面加入：

```typescript
      const addendum = readHead(join(HARNESS_ROOT, "pi-rules"), "case-autonomous-execution.md", MAX_INJECT_CHARS);

      if (addendum.trim()) {
        parts.push(
          "",
          "---BEGIN C.A.S.E. HARNESS ADDENDUM (supersedes conflicting instructions above on DONE-gating and retrospectives)---",
          addendum.trim(),
          "---END C.A.S.E. HARNESS ADDENDUM---"
        );
      }
```

完整區塊修改後應為：

```typescript
    if (isCaseProject(ctx.cwd)) {
      const constitution = readHead(join(ctx.cwd, "00_Constitution"), "core.md", MAX_INJECT_CHARS);
      const roadmap = readHead(join(ctx.cwd, "01_Roadmap"), "roadmap.md", MAX_INJECT_CHARS);
      const addendum = readHead(join(HARNESS_ROOT, "pi-rules"), "case-autonomous-execution.md", MAX_INJECT_CHARS);

      if (constitution.trim()) {
        parts.push(
          "",
          "---BEGIN C.A.S.E. CONSTITUTION---",
          constitution.trim(),
          "---END C.A.S.E. CONSTITUTION---"
        );
      }
      if (roadmap.trim()) {
        parts.push(
          "",
          "---BEGIN C.A.S.E. ROADMAP---",
          roadmap.trim(),
          "---END C.A.S.E. ROADMAP---"
        );
      }
      if (addendum.trim()) {
        parts.push(
          "",
          "---BEGIN C.A.S.E. HARNESS ADDENDUM (supersedes conflicting instructions above on DONE-gating and retrospectives)---",
          addendum.trim(),
          "---END C.A.S.E. HARNESS ADDENDUM---"
        );
      }
    }
```

- [ ] **Step 4: 執行測試確認通過**

Run: `python -m unittest tests.test_case_bridge -v`
Expected: 全部 7 個測試 PASS

- [ ] **Step 5: 用 jiti loader 實際載入驗證（比照稍早 stealth-web-bridge/yes-hooks-bridge 的驗證方式）**

建立暫存腳本 `/tmp/verify_case_bridge.mjs`（驗證用，不納入 repo）：

```javascript
import { pathToFileURL } from "node:url";
const jitiUrl = pathToFileURL("C:/Users/User/AppData/Roaming/npm/node_modules/@earendil-works/pi-coding-agent/node_modules/jiti/lib/jiti.mjs").href;
const { createJiti } = await import(jitiUrl);
const jiti = createJiti(import.meta.url, { interopDefault: true });

const mod = await jiti.import(pathToFileURL("D:/MyProject/CKs_PI_Code_Agent_Harness/pi-extensions/case-bridge/index.ts").href);
const factory = mod.default ?? mod;

let beforeAgentStartHandler;
const stubPi = { on: (name, fn) => { if (name === "before_agent_start") beforeAgentStartHandler = fn; } };
factory(stubPi);

// 需要一個假的 00_Constitution 目錄讓 isCaseProject() 判斷為 true
import { mkdtempSync, writeFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
const cwd = mkdtempSync(join(tmpdir(), "case-test-"));
mkdirSync(join(cwd, "00_Constitution"));
writeFileSync(join(cwd, "00_Constitution", "core.md"), "test constitution");

const ctx = { cwd };
const result = beforeAgentStartHandler({ systemPrompt: "" }, ctx);
console.log("has addendum marker:", result.systemPrompt.includes("BEGIN C.A.S.E. HARNESS ADDENDUM"));
console.log("has DONE gate text:", result.systemPrompt.includes("DONE 閘門鬆綁"));
```

Run: `node /tmp/verify_case_bridge.mjs`
Expected: `has addendum marker: true` 與 `has DONE gate text: true`（若失敗，檢查 `case-bridge/index.ts` 內 `require.resolve("./package.json")` 在暫存腳本情境下的路徑解析是否符合預期，必要時直接在真實 Pi session 手動驗證取代此步驟）

- [ ] **Step 6: Commit**

```bash
git add pi-extensions/case-bridge/index.ts tests/test_case_bridge.py
git commit -m "feat(case): inject autonomous-execution addendum into CASE project system prompt"
```

---

## Self-Review Notes

- Spec 覆蓋：spec 的「DONE 閘門鬆綁」「強制復盤」「連續執行授權」三點都在 Task 1 的協定內容裡逐條落實；「疊加不覆蓋、不動 submodule」在 Task 2 落實（讀取來源是 `HARNESS_ROOT/pi-rules`，`external/Local-Agent-Workspace` 完全沒被 Modify）。
- 型別/名稱一致性：`readHead`/`isCaseProject`/`HARNESS_ROOT` 全部沿用 `case-bridge/index.ts` 既有定義，Task 2 沒有引入任何新的 helper 或改變既有函式簽章。
- Task 2 Step 5 的驗證腳本屬於人工確認步驟（比照今晚稍早驗證 stealth-web-bridge/yes-hooks-bridge 的方式），不是自動化測試的一部分，執行後不需要保留產物。
