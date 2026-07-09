# thinking-frameworks Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增一個無冒名的 `thinking-frameworks` skill(西方決策心智模型快速自我檢查),補 qiushi/mece 未涵蓋的那一味。

**Architecture:** 純 Markdown 本地 skill,放 `pi-skills/optional/`(standard 層,minimal 不吃);pi 自動掃描載入,無需改 restore.py/settings。附零依賴 unittest。

**Tech Stack:** Markdown、Python 標準庫 unittest。

## Global Constraints

- 零冒名:不得出現「我是/作為/扮演 <真人名>」「You are <RealPerson>」「act as 」。
- 零建議責任:明文「純推理工具、不提供投資/醫療/法律建議」。
- 純 Markdown、零依賴;測試用 `unittest`(不引入 pytest)。
- 中文用臺灣正體;不硬編機器路徑(無 `file:///[A-Za-z]:/`、`[A-Za-z]:/MyProject`)。
- 分工明文:重取捨→`mece-autopilot`;辯證→`qiushi`;本 skill=快速個人透鏡。
- 本機 Python:`C:/Users/User/AppData/Local/Python/bin/python.exe`(`python` 為失效 stub)。
- Git 身分已設 `Chiakai Chang <lotifv@gmail.com>`。

## File Structure

- `pi-skills/optional/thinking-frameworks/SKILL.md` — skill 主體(frontmatter + 何時用 + 7 工具 + 邊界)。
- `pi-skills/optional/thinking-frameworks/RATIONALE.md` — 決策脈絡。
- `tests/test_thinking_frameworks.py` — 零依賴 unittest。

---

### Task 1: thinking-frameworks skill + 測試

**Files:**
- Create: `pi-skills/optional/thinking-frameworks/SKILL.md`
- Create: `pi-skills/optional/thinking-frameworks/RATIONALE.md`
- Create: `tests/test_thinking_frameworks.py`

**Interfaces:**
- Produces: 一個 pi 可自動掃描載入的 markdown skill(standard profile)。無程式介面。

- [ ] **Step 1: 寫失敗測試**

新建 `tests/test_thinking_frameworks.py`:

```python
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = "pi-skills/optional/thinking-frameworks/SKILL.md"
RATIONALE = "pi-skills/optional/thinking-frameworks/RATIONALE.md"


def read_file(rel):
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as f:
        return f.read()


class TestThinkingFrameworks(unittest.TestCase):
    def test_skill_exists_and_named(self):
        self.assertIn("name: thinking-frameworks", read_file(SKILL))

    def test_seven_frameworks_present(self):
        c = read_file(SKILL)
        for kw in ["反演", "基準率", "二階", "機會成本", "第一性", "偏誤", "可證偽"]:
            self.assertIn(kw, c, f"missing framework: {kw}")

    def test_division_of_labor(self):
        c = read_file(SKILL).lower()
        self.assertIn("mece", c)
        self.assertIn("qiushi", c)

    def test_boundary_present(self):
        c = read_file(SKILL)
        self.assertIn("不冒名", c)
        self.assertIn("純推理工具", c)
        self.assertIn("不提供投資", c)

    def test_no_impersonation_patterns(self):
        c = read_file(SKILL)
        for bad in ["我是巴菲特", "作為巴菲特", "扮演巴菲特",
                    "You are Warren Buffett", "act as "]:
            self.assertNotIn(bad, c, f"impersonation pattern present: {bad}")

    def test_no_machine_paths(self):
        for rel in (SKILL, RATIONALE):
            self.assertIsNone(
                re.search(r"file:///[A-Za-z]:/|[A-Za-z]:/MyProject", read_file(rel)),
                f"{rel} has a machine-specific path",
            )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_thinking_frameworks -v`
Expected: FAIL(檔案不存在 → FileNotFoundError)

- [ ] **Step 3a: 建立 `SKILL.md`**

`pi-skills/optional/thinking-frameworks/SKILL.md`:

````markdown
---
name: thinking-frameworks
description: 日常非瑣碎決策的快速心智模型自我檢查(反演/基準率/二階效應/機會成本/第一性原理/偏誤檢查/可證偽)。重取捨或多方利害請升級 mece-autopilot;辯證分析用 qiushi。純推理工具,不冒名真人、不給投資/醫療/法律建議。
---

# thinking-frameworks — 快速決策自我檢查

純推理透鏡:做**日常非瑣碎**的判斷、取捨、評估時,快速過一遍下列模型,減少盲點。

## 何時用
- 快速的非瑣碎判斷/取捨/評估 → 過一遍本清單(幾秒到一兩分鐘)。
- **牽涉多方利害、複雜或高風險取捨 → 升級 `mece-autopilot`**(動態多角色辯論)。
- 需要辯證/矛盾分析 → 用 `qiushi`。
- 瑣碎、純機械任務 → 不需要。

## 七個工具(各問自己一句)
1. **反演**:什麼會「保證失敗」?先列出,再刻意避開。
2. **基準率 / 外部視角**:同類事情一般的成功/失敗機率是多少?別只信眼前這個故事。
3. **二階效應**:這步之後會連鎖出什麼?下游、長期、他人的反應。
4. **機會成本**:選這個 = 放棄了哪個更好的選項?
5. **第一性原理**:拆到根本事實重新推,而非照類比、慣例或「大家都這樣」。
6. **認知偏誤檢查**:我是否中了——確認偏誤(只找支持證據)、沉沒成本、錨定、過度自信、可得性(被最近/顯眼的例子帶偏)?
7. **可證偽**:什麼證據會讓我改變主意?主動去找那個反證。

## 邊界
- 純推理工具,**不冒名、不扮演任何真實人物**。
- **不提供投資、醫療、法律建議**;財務/健康/法律決策請洽合格專業人士。
- 不取代 `mece-autopilot`(群體對抗辯論)與 `qiushi`(辯證法)——本 skill 是它們之下的快速個人透鏡,分工不重疊。
````

（注意:寫入時去掉最外層 ````markdown 包裹,只留內層 `---` frontmatter 起始的內容。）

- [ ] **Step 3b: 建立 `RATIONALE.md`**

`pi-skills/optional/thinking-frameworks/RATIONALE.md`:

```markdown
# RATIONALE: thinking-frameworks

## 決策脈絡
評估 7 個「名人蒸餾人格」repo 後全部否決(見 `docs/decisions/2026-07-09-persona-skills-evaluation.md`)。使用者要「那批 repo 想指向、但乾淨」的版本 = 心智模型當推理工具、不冒名真人。

## 為何做(路徑判定:原生撰寫 clean-room)
- **gap 屬實**:全 skill 空間查證,西方決策心智模型/認知偏誤無人涵蓋(`qiushi` 是辯證法;`recursive-decision-ledger`/`architecture-decision-records` 只管記錄決策)。
- **與既有分工**:`mece-autopilot` = 重量級群體對抗辯論(複雜取捨);本 skill = 日常小決策的快速個人透鏡,重取捨升級 mece;`qiushi` = 辯證分析。三者不同量級、互補。
- **無責任**:不冒名任何真人、不給投資/醫療/法律建議,避開名人人格 repo 的 IP/冒名/建議責任。

## 設計脈絡(dogfood qiushi+mece)
初版設計「不加觸發以免撞 mece」被 mece 魔鬼代言人揪出致命弱點:無觸發=沒人用=裝飾。重塑為「mece 之下的快速透鏡」:靠 skill 自身「何時用」引導、重取捨明文升級 mece,取得非重疊生態位。

## 維護
純 Markdown、零依賴、無外部上游。內容穩定,少需更動;新增框架時保持「高信號、可即用」,勿膨脹成百科。
```

- [ ] **Step 4: 跑測試確認通過**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest tests.test_thinking_frameworks -v`
Expected: PASS(6 測試全過)

- [ ] **Step 5: 全套 + 反冒名 grep + 沙盒載入驗證**

Run: `C:/Users/User/AppData/Local/Python/bin/python.exe -m unittest discover -s tests`
Expected: 全綠

Run: `grep -rn "扮演[^任]\|我是.*巴菲特\|act as " pi-skills/optional/thinking-frameworks`
Expected: 無命中(「不扮演任何真實人物」中的「扮演任」不算冒名)

沙盒 restore(確認 standard 載入、minimal 不載入):
```bash
SB="C:/Users/User/AppData/Local/Temp/claude/D--MyProject-CKs-PI-Code-Agent-Harness/d13564fd-f2dd-4046-addc-fe706e926e12/scratchpad/sbtf"
rm -rf "$SB"; HOME="$SB" USERPROFILE="$SB" C:/Users/User/AppData/Local/Python/bin/python.exe scripts/restore.py --auto --profile standard >/dev/null 2>&1
ls "$SB/.pi/agent/skills/thinking-frameworks/SKILL.md" && echo "standard: 載入 OK"
rm -rf "$SB"; HOME="$SB" USERPROFILE="$SB" C:/Users/User/AppData/Local/Python/bin/python.exe scripts/restore.py --auto --profile minimal >/dev/null 2>&1
ls "$SB/.pi/agent/skills/thinking-frameworks/SKILL.md" 2>&1 | grep -q "No such" && echo "minimal: 未載入 OK(正確)"
```
Expected: standard 有、minimal 無。

- [ ] **Step 6: Commit**

```bash
git add pi-skills/optional/thinking-frameworks tests/test_thinking_frameworks.py
git commit -m "feat(thinking-frameworks): add impersonation-free mental-models lens skill"
```

---

## Self-Review

**1. Spec coverage:**
- SKILL.md(frontmatter/何時用/7 工具/邊界)→ Task 1 Step 3a。
- RATIONALE.md → Step 3b。
- 放 optional(standard 層,minimal 不吃)→ 沙盒驗證 Step 5。
- 7 框架、分工、邊界、反冒名、平台無關 → 測試 Step 1。
- 零依賴 unittest → 全程。
- 無需改 restore.py/settings → 檔案清單未列,沙盒驗證確認自動載入。無缺口。

**2. Placeholder scan:** 無 TBD/TODO;SKILL.md/RATIONALE.md/測試皆完整內容。

**3. Type consistency:** 路徑 `pi-skills/optional/thinking-frameworks/{SKILL.md,RATIONALE.md}`、測試常數 `SKILL`/`RATIONALE`、關鍵字清單、邊界字樣(不冒名/純推理工具/不提供投資)全計畫一致;反冒名樣式清單與 SKILL 邊界用語(「不扮演任何真實人物」不觸發帶名樣式)相容。
