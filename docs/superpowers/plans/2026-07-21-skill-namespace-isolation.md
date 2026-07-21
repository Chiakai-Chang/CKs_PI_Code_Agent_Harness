# Skill 撞名隔離 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `external/*` submodule skill 不再被 restore.py 一次性寫死進全域 `settings.json`；改成 restore.py 只決定「這個 profile 要哪些 external skill」寫成清單，新的 `skill-namespace-guard` extension 在**每次** pi 啟動時即時比對是否撞名，撞名內容相同就去重、不同才隔離改名。

**Architecture:** `restore.py` 新增一個純函式把 `profile_skills` 按來源（`ext_root` vs `pi_skills_root`）拆開，`ext_root` 那批寫進新檔 `pi-config/external-skills-manifest.json`，不再進 `settings.json`。新 extension `skill-namespace-guard` 掛 Pi 的 `resources_discover` 事件，讀這份清單，逐一比對 `~/.pi/agent/skills/<name>/`，回傳最終要用的 `skillPaths`。

**Tech Stack:** Python 3 標準庫（`restore.py`）、TypeScript Pi extension、`node:crypto`（sha256）、`unittest`。

## Global Constraints

- 零依賴；Python 測試用 `unittest`，不引入 pytest。
- 不改變 `pi-skills/core/*` 現有的 `managed_skills` 物理複製機制。
- 不掃描 `~/.agents/skills/`、專案層級 `.pi/skills/`（YAGNI，範圍只到 `~/.pi/agent/skills/`）。
- 平台無關：不硬編機器路徑。
- Windows 換行問題：所有跨檔案內容比對前先正規化 `\r\n` → `\n`。

## File Structure

- `scripts/restore.py` — 修改：新增 `partition_external_skills()` 純函式；`profile_skills` 建立完後呼叫它拆分；寫 `pi-config/external-skills-manifest.json`；`skill-namespace-guard` 加進三處註冊（`profile_extensions.append`／`internal_bridge_names`／delete loop）。
- `pi-extensions/skill-namespace-guard/index.ts` — 新增：`resources_discover` handler，含 `readFrontmatterName`／`patchSkillName`／`normalizedHash`／`stageRenamedSkill`。
- `pi-extensions/skill-namespace-guard/package.json` — 新增：比照既有 bridge 格式。
- `tests/test_restore.py` — 延伸：`partition_external_skills` 測試、三處註冊測試。
- `tests/test_skill_namespace_guard.py` — 新增：contract test（比照 `test_yes_hooks_bridge.py` 風格）。

---

### Task 1: `restore.py` — 拆分 external skills、寫 manifest、三處註冊新 extension

**Files:**
- Modify: `scripts/restore.py`
- Test: `tests/test_restore.py`

**Interfaces:**
- Produces: `partition_external_skills(profile_skills: list[str], ext_root: str) -> tuple[list[str], list[str]]`（回傳 `(internal, external)`，用 `str.startswith(ext_root)` 判斷歸屬）。
- Produces: `pi-config/external-skills-manifest.json`，格式 `[{"path": "<abs path>"}, ...]`。

- [ ] **Step 1: 寫失敗測試**

在 `tests/test_restore.py` 新增：

```python
class TestPartitionExternalSkills(unittest.TestCase):
    def test_splits_by_ext_root_prefix(self):
        ext_root = "/repo/external"
        pi_skills_root = "/repo/pi-skills"
        profile_skills = [
            f"{pi_skills_root}/chrome-cdp",
            f"{ext_root}/caveman/skills/caveman",
            f"{pi_skills_root}/graphify",
            f"{ext_root}/darwin-skill",
        ]
        internal, external = restore.partition_external_skills(profile_skills, ext_root)
        self.assertEqual(internal, [f"{pi_skills_root}/chrome-cdp", f"{pi_skills_root}/graphify"])
        self.assertEqual(external, [f"{ext_root}/caveman/skills/caveman", f"{ext_root}/darwin-skill"])

    def test_empty_input(self):
        internal, external = restore.partition_external_skills([], "/repo/external")
        self.assertEqual(internal, [])
        self.assertEqual(external, [])


class TestSkillNamespaceGuardWiring(unittest.TestCase):
    def test_registered_in_three_sites(self):
        c = read_file("scripts/restore.py")
        self.assertEqual(c.count('"skill-namespace-guard"'), 3)

    def test_manifest_write_present(self):
        c = read_file("scripts/restore.py")
        self.assertIn("external-skills-manifest.json", c)
        self.assertIn("partition_external_skills(", c)
```

`tests/test_restore.py` 目前沒有共用的原始碼讀取 helper（既有測試多半 `import restore` 後直接呼叫函式；唯一一處讀檔是 `TestConfigHygiene._packages` 內的 inline `open(...)`）。在 `ROOT = ...`（第 5 行）之後、第一個 `class` 定義之前，新增一個模組層級的小 helper 供 `TestSkillNamespaceGuardWiring` 使用：

```python
def read_file(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python -m unittest tests.test_restore -v`
Expected: FAIL — `AttributeError: module 'restore' has no attribute 'partition_external_skills'`

- [ ] **Step 3: 在 `restore.py` 新增 `partition_external_skills`**

在檔案任何既有 helper 函式群組附近（例如 `merge_settings` 定義之後）新增：

```python
def partition_external_skills(profile_skills, ext_root):
    """Split profile_skills by source: pi_skills_root-authored ones stay
    registered directly (safe, harness-owned names); ext_root submodule ones
    carry generic upstream names and go through skill-namespace-guard's live
    collision check instead of a one-time restore-time snapshot."""
    internal = [p for p in profile_skills if not p.startswith(ext_root)]
    external = [p for p in profile_skills if p.startswith(ext_root)]
    return internal, external
```

- [ ] **Step 4: 執行測試確認 `TestPartitionExternalSkills` 通過**

Run: `python -m unittest tests.test_restore.TestPartitionExternalSkills -v`
Expected: PASS

- [ ] **Step 5: 在主流程接上拆分邏輯與 manifest 寫檔**

在 `scripts/restore.py` 的 `profile_skills`/`profile_extensions` 建立區塊（`if profile == "minimal": ... elif profile == "standard": ...` 那個 if/elif 結束之後，「3. Filter existing settings」區塊開始之前，也就是既有第 534/548 行之後、第 552 行之前）插入：

```python
    # 2a. Partition external/* skills out of profile_skills: they carry generic
    # upstream names and can silently shadow anything the user independently
    # installs later. skill-namespace-guard live-detects collisions with them
    # at every session start instead of restore.py deciding once, frozen.
    profile_skills, profile_skills_external = partition_external_skills(profile_skills, ext_root)

    manifest_path = os.path.join(REPO_ROOT, "pi-config", "external-skills-manifest.json")
    save_json(manifest_path, [{"path": p} for p in profile_skills_external])
    log(f"  - external-skills-manifest.json written ({len(profile_skills_external)} entries)")

    # skill-namespace-guard re-registers the external/* skills above (collision-
    # checked, live) — required regardless of profile since minimal also has an
    # ext_root skill (caveman).
    profile_extensions.append(os.path.join(pi_extensions_root, "skill-namespace-guard").replace("\\", "/"))
```

- [ ] **Step 6: 更新 `internal_bridge_names`（既有第 563 行）**

```python
        internal_bridge_names = ["ecc-hooks-bridge", "planning-with-files-bridge", "case-bridge", "taste-bridge", "mece-autopilot-bridge", "stealth-web-bridge", "yes-hooks-bridge", "skill-namespace-guard"]
```

- [ ] **Step 7: 更新 delete loop（既有第 680 行）**

```python
        for bridge in ["ecc-hooks-bridge", "planning-with-files-bridge", "case-bridge", "taste-bridge", "mece-autopilot-bridge", "stealth-web-bridge", "yes-hooks-bridge", "skill-namespace-guard"]:
```

- [ ] **Step 8: 執行全部測試確認通過**

Run: `python -m unittest tests.test_restore -v`
Expected: 全部 PASS（含 `TestSkillNamespaceGuardWiring` 的 2 個測試）

- [ ] **Step 9: Commit**

```bash
git add scripts/restore.py tests/test_restore.py
git commit -m "feat(restore): partition external/* skills out of settings.json into a manifest"
```

---

### Task 2: `skill-namespace-guard` extension — 即時撞名偵測與隔離

**Files:**
- Create: `pi-extensions/skill-namespace-guard/index.ts`
- Create: `pi-extensions/skill-namespace-guard/package.json`
- Create: `tests/test_skill_namespace_guard.py`

**Interfaces:**
- Consumes: `pi-config/external-skills-manifest.json`（Task 1 產出，格式 `[{"path": string}]`）。
- Produces: `pi.on("resources_discover", handler)`，`handler` 回傳 `{ skillPaths: string[] }`。

- [ ] **Step 1: 寫 contract test（先於程式碼，比照既有 bridge 測試風格）**

新建 `tests/test_skill_namespace_guard.py`：

```python
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class TestSkillNamespaceGuardContract(unittest.TestCase):
    IDX = "pi-extensions/skill-namespace-guard/index.ts"
    PKG = "pi-extensions/skill-namespace-guard/package.json"

    def test_hooks_resources_discover(self):
        c = read(self.IDX)
        self.assertIn('pi.on("resources_discover"', c)

    def test_reads_manifest(self):
        c = read(self.IDX)
        self.assertIn("external-skills-manifest.json", c)

    def test_reads_frontmatter_name(self):
        c = read(self.IDX)
        self.assertIn("function readFrontmatterName", c)

    def test_hashes_normalized_content(self):
        c = read(self.IDX)
        self.assertIn("function normalizedHash", c)
        self.assertIn('replace(/\\r\\n/g, "\\n")', c)

    def test_stages_renamed_copy_on_collision(self):
        c = read(self.IDX)
        self.assertIn("function stageRenamedSkill", c)
        self.assertIn("harness-${name}", c)

    def test_skips_duplicate_on_identical_content(self):
        c = read(self.IDX)
        self.assertIn("continue", c)  # identical-hash branch skips registration

    def test_fails_open_on_missing_name(self):
        c = read(self.IDX)
        self.assertIn("Could not read name:", c)

    def test_package_is_esm_with_harness_root(self):
        pkg = read(self.PKG)
        self.assertIn('"type": "module"', pkg)
        self.assertIn("pi-harness", pkg)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python -m unittest tests.test_skill_namespace_guard -v`
Expected: FAIL — `FileNotFoundError`（extension 還不存在）

- [ ] **Step 3: 建立 `package.json`**

新建 `pi-extensions/skill-namespace-guard/package.json`：

```json
{
  "name": "skill-namespace-guard",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "main": "index.ts",
  "pi-harness": {
    "root": "TODO_SET_BY_RESTORE"
  }
}
```

- [ ] **Step 4: 建立 `index.ts`**

新建 `pi-extensions/skill-namespace-guard/index.ts`：

```typescript
/**
 * Skill Namespace Guard Extension
 *
 * external/* submodule skills carry generic upstream names (agents-best-
 * practices, darwin-skill, superpowers's brainstorming, ...). restore.py no
 * longer registers them directly in settings.json — it writes their paths to
 * pi-config/external-skills-manifest.json instead, and this extension
 * resolves them live on every resources_discover (session start/reload):
 *
 *   - No existing global skill with that name → register the raw path.
 *   - Existing global skill, identical content → skip (don't duplicate;
 *     the user's own independent install already covers it).
 *   - Existing global skill, different content → stage an isolated copy at
 *     ~/.pi/agent/skills/harness-<name>/ with a patched name: frontmatter,
 *     leave the user's original untouched, register the staged copy.
 *
 * This re-runs every session, unlike a restore-time-only check, so it keeps
 * catching collisions introduced by anything the user installs independently
 * between harness updates.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { readFileSync, existsSync, mkdirSync, cpSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { homedir } from "node:os";
import { createHash } from "node:crypto";

interface ManifestEntry {
  path: string;
}

function harnessRoot(): string {
  const here = dirname(fileURLToPath(import.meta.url));
  try {
    const pkg = JSON.parse(readFileSync(join(here, "package.json"), "utf-8"));
    if (pkg["pi-harness"]?.root) return pkg["pi-harness"].root;
  } catch {}
  return join(here, "../..");
}

function readManifest(): ManifestEntry[] {
  const manifestPath = join(harnessRoot(), "pi-config", "external-skills-manifest.json");
  if (!existsSync(manifestPath)) return [];
  try {
    return JSON.parse(readFileSync(manifestPath, "utf-8"));
  } catch {
    return [];
  }
}

// Extracts the frontmatter `name:` field. SKILL.md format per docs/skills.md:
// "---\nname: my-skill\ndescription: ...\n---". Returns null if unparseable
// (fail open — caller registers the raw path unchanged rather than dropping
// the skill).
function readFrontmatterName(skillMdPath: string): string | null {
  if (!existsSync(skillMdPath)) return null;
  let raw: string;
  try {
    raw = readFileSync(skillMdPath, "utf-8");
  } catch {
    return null;
  }
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) return null;
  const nameMatch = match[1].match(/^name:\s*(.+?)\s*$/m);
  return nameMatch ? nameMatch[1].trim() : null;
}

// Rewrites only the frontmatter block's name: field, leaving the rest of the
// file (body, other frontmatter fields) untouched. If no name: field exists
// in the frontmatter, prepends one.
function patchSkillName(rawContent: string, newName: string): string {
  const match = rawContent.match(/^(---\r?\n)([\s\S]*?)(\r?\n---)([\s\S]*)$/);
  if (!match) return rawContent;
  const [, open, frontmatter, close, rest] = match;
  const patched = /^name:\s*.+$/m.test(frontmatter)
    ? frontmatter.replace(/^name:\s*.+$/m, `name: ${newName}`)
    : `name: ${newName}\n${frontmatter}`;
  return `${open}${patched}${close}${rest}`;
}

function normalizedHash(content: string): string {
  const normalized = content.replace(/\r\n/g, "\n").trim();
  return createHash("sha256").update(normalized, "utf-8").digest("hex");
}

// Stages an isolated, renamed copy at ~/.pi/agent/skills/harness-<name>/.
// Idempotent: if the destination already holds exactly what we'd produce
// (from a prior session), skips the copy — avoids redundant disk I/O on
// every startup and never re-flags its own prior output as a new collision.
function stageRenamedSkill(srcDir: string, name: string, srcRaw: string): string {
  const destDir = join(homedir(), ".pi", "agent", "skills", `harness-${name}`);
  const destSkillMd = join(destDir, "SKILL.md");
  const expected = patchSkillName(srcRaw, `harness-${name}`);

  if (existsSync(destSkillMd) && readFileSync(destSkillMd, "utf-8") === expected) {
    return destDir;
  }

  mkdirSync(destDir, { recursive: true });
  cpSync(srcDir, destDir, { recursive: true });
  writeFileSync(destSkillMd, expected, "utf-8");
  return destDir;
}

export default function (pi: ExtensionAPI) {
  pi.on("resources_discover", async (_event, ctx) => {
    const manifest = readManifest();
    const skillPaths: string[] = [];

    for (const { path: srcDir } of manifest) {
      const srcSkillMd = join(srcDir, "SKILL.md");
      const name = readFrontmatterName(srcSkillMd);

      if (!name) {
        ctx.ui.notify(`[skill-namespace-guard] Could not read name: from ${srcSkillMd}; registering as-is.`, "warning");
        skillPaths.push(srcDir);
        continue;
      }

      const existingSkillMd = join(homedir(), ".pi", "agent", "skills", name, "SKILL.md");
      if (!existsSync(existingSkillMd)) {
        skillPaths.push(srcDir);
        continue;
      }

      const srcRaw = readFileSync(srcSkillMd, "utf-8");
      const existingRaw = readFileSync(existingSkillMd, "utf-8");

      if (normalizedHash(existingRaw) === normalizedHash(srcRaw)) {
        // Same skill, already installed independently — don't duplicate.
        continue;
      }

      const stagedDir = stageRenamedSkill(srcDir, name, srcRaw);
      skillPaths.push(stagedDir);
      ctx.ui.notify(
        `[skill-namespace-guard] "${name}" collides with an existing global skill of different content — registered isolated copy as "harness-${name}".`,
        "warning",
      );
    }

    return { skillPaths };
  });
}
```

- [ ] **Step 5: 執行測試確認通過**

Run: `python -m unittest tests.test_skill_namespace_guard -v`
Expected: 全部 8 個測試 PASS

- [ ] **Step 6: 用 jiti loader 實際跑三種情境（無撞名／撞名相同／撞名不同）**

建立暫存驗證腳本 `/tmp/verify_skill_guard.mjs`（驗證用，不納入 repo）：

```javascript
import { pathToFileURL } from "node:url";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

// Redirect homedir() to a sandbox so this never touches the real ~/.pi.
const fakeHome = mkdtempSync(join(tmpdir(), "skill-guard-home-"));
process.env.HOME = fakeHome;
process.env.USERPROFILE = fakeHome;
mkdirSync(join(fakeHome, ".pi", "agent", "skills"), { recursive: true });

const jitiUrl = pathToFileURL("C:/Users/User/AppData/Roaming/npm/node_modules/@earendil-works/pi-coding-agent/node_modules/jiti/lib/jiti.mjs").href;
const { createJiti } = await import(jitiUrl);
const jiti = createJiti(import.meta.url, { interopDefault: true });

// Build a fake external skill + fake manifest + fake package.json pointing at it.
const harnessRoot = mkdtempSync(join(tmpdir(), "skill-guard-harness-"));
mkdirSync(join(harnessRoot, "pi-config"), { recursive: true });

function makeSkill(dir, name, body) {
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, "SKILL.md"), `---\nname: ${name}\ndescription: test skill\n---\n\n${body}`);
}

// Case 1: no collision.
const skillA = join(harnessRoot, "external", "skill-a");
makeSkill(skillA, "skill-a", "content A");

// Case 2: collision, identical content.
const skillB = join(harnessRoot, "external", "skill-b");
makeSkill(skillB, "skill-b", "content B");
makeSkill(join(fakeHome, ".pi", "agent", "skills", "skill-b"), "skill-b", "content B");

// Case 3: collision, different content.
const skillC = join(harnessRoot, "external", "skill-c");
makeSkill(skillC, "skill-c", "content C from harness");
makeSkill(join(fakeHome, ".pi", "agent", "skills", "skill-c"), "skill-c", "content C from someone else");

writeFileSync(
  join(harnessRoot, "pi-config", "external-skills-manifest.json"),
  JSON.stringify([{ path: skillA }, { path: skillB }, { path: skillC }]),
);

const extDir = join(harnessRoot, "pi-extensions", "skill-namespace-guard");
mkdirSync(extDir, { recursive: true });
writeFileSync(join(extDir, "package.json"), JSON.stringify({ "pi-harness": { root: harnessRoot } }));

const realIndexTs = readFileSync("D:/MyProject/CKs_PI_Code_Agent_Harness/pi-extensions/skill-namespace-guard/index.ts", "utf-8");
writeFileSync(join(extDir, "index.ts"), realIndexTs);

const mod = await jiti.import(pathToFileURL(join(extDir, "index.ts")).href);
const factory = mod.default ?? mod;

let handler;
const notifications = [];
const stubPi = { on: (name, fn) => { if (name === "resources_discover") handler = fn; } };
factory(stubPi);

const ctx = { ui: { notify: (msg, level) => notifications.push({ msg, level }) } };
const result = await handler({ reason: "startup" }, ctx);

console.log("skillPaths:", result.skillPaths);
console.log("expect skill-a raw path present:", result.skillPaths.includes(skillA));
console.log("expect skill-b NOT present (deduped):", !result.skillPaths.includes(skillB));
console.log("expect harness-skill-c staged path present:", result.skillPaths.some(p => p.includes("harness-skill-c")));
console.log("staged skill-c content:", readFileSync(join(fakeHome, ".pi", "agent", "skills", "harness-skill-c", "SKILL.md"), "utf-8"));
console.log("notifications:", notifications);
```

Run: `node /tmp/verify_skill_guard.mjs`
Expected:
- `expect skill-a raw path present: true`
- `expect skill-b NOT present (deduped): true`
- `expect harness-skill-c staged path present: true`
- 印出的 `staged skill-c content` 裡 `name:` 欄位是 `harness-skill-c`，本文 `content C from harness` 完整保留
- `notifications` 陣列裡有一則關於 `skill-c` 撞名的 warning

- [ ] **Step 7: Commit**

```bash
git add pi-extensions/skill-namespace-guard/ tests/test_skill_namespace_guard.py
git commit -m "feat(skills): live collision detection + isolation via resources_discover"
```

---

## Self-Review Notes

- Spec 覆蓋：spec 的「即時判斷（非安裝時快照）」→ Task 2 用 `resources_discover`；「external/* 全範圍」→ Task 1 用 `startswith(ext_root)` 涵蓋所有來源，不只兩個範例；「restore.py 不再雙重註冊」→ Task 1 Step 5 直接把 external 那批從 `profile_skills` 移除（`partition_external_skills` 回傳值取代原變數），不是額外新增一份，原本會流進 `settings.json` 的路徑不會再包含它們；「新 extension 強制裝上」→ Task 1 Step 5–7 三處註冊。
- 相較於 spec 原文的簡化：spec 提到用「名字有沒有 `harness-` 字首」判斷是否為自己的產出；實作時發現不需要——因為程式只會寫入 `harness-<name>` 這個路徑，從不寫入裸 `<name>`，所以在裸 `<name>` 位置找到的任何東西必然不是自己的產出，不需要額外判斷分支。冪等性改由 `stageRenamedSkill` 內部「目的地內容已符合預期就跳過複製」達成，邏輯更簡單且行為等價。
- 型別/名稱一致性：`partition_external_skills` 回傳順序 `(internal, external)`，Task 1 Step 5 `profile_skills, profile_skills_external = partition_external_skills(...)` 對應正確；`stageRenamedSkill(srcDir, name, srcRaw)` 三個參數在定義與呼叫處一致。
- Task 2 Step 6 的驗證腳本用 `HOME`/`USERPROFILE` 環境變數重導向，確保測試不會寫到使用者真實的 `~/.pi/agent/skills/`。
