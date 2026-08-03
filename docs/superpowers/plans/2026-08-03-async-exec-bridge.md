# async-exec-bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the agent dispatch long-running work, stop cleanly, and resume by itself when that work finishes — so a slow model never also means a human stuck watching it.

**Architecture:** One new Pi extension, `pi-extensions/async-exec-bridge`. Pure logic lives in small sibling modules with no Pi dependency (job store, lease, envelope, preflight, state block); `index.ts` holds only Pi wiring — three tools plus lifecycle hooks. All job state is written to disk as the source of truth, so a crash can be reconciled and a future daemon can read the same files. Completion wakes the agent via `pi.sendMessage(..., { deliverAs: "followUp", triggerTurn: true })`.

**Tech Stack:** TypeScript (run by Pi's own loader), Node's built-in test runner for unit tests, Python `unittest` for the repo's existing contract/wiring tests. No new dependencies.

**Spec:** [docs/superpowers/specs/2026-08-03-async-resumable-execution-design.md](../specs/2026-08-03-async-resumable-execution-design.md)

## Global Constraints

- **Language:** All prose in this repo is 正體中文 with Taiwan terminology and full-width punctuation. Code, identifiers, and commit messages stay English. (`pi-rules/AGENTS.md` §0)
- **Shell:** Git Bash. Forward slashes, UNIX utilities. Never PowerShell or CMD. (`pi-rules/AGENTS.md` §1)
- **Commits:** `<type>: <description>`. Types: feat, fix, refactor, docs, test, chore, perf, ci. **Attribution is disabled globally — no Co-Authored-By trailer.** (`pi-rules/git-workflow.md`)
- **Import extensions:** Inside this bridge, sibling imports use the explicit `.ts` extension (`import { x } from "./jobs.ts"`). Verified to work under both Pi's loader and `node --test`. Do **not** copy `deep-research-bridge`'s `./research.js` style — that does not resolve under `node --test`.
- **Pi API shapes** (read from the installed `@earendil-works/pi-coding-agent/dist/core/extensions/types.d.ts`, not from memory):
  - `pi.registerTool(tool)` takes **one object**: `{ name, label, description, promptSnippet?, promptGuidelines?, parameters: Type.Object({...}), async execute(toolCallId, params, signal, onUpdate, ctx) }`. There is no `(name, {handler})` two-argument form. `parameters` is a TypeBox schema and is **required** — without it the model has no way to pass arguments.
  - `execute` returns `AgentToolResult`: `{ content: [{ type: "text", text }], details? }`. Not a bare string.
  - `session_start` is `ExtensionHandler<SessionStartEvent>` with `R = undefined` — **its return value is discarded**. Only `before_agent_start` accepts `{ message }` (`BeforeAgentStartEventResult`).
  - `ctx.getContextUsage()` returns `{ tokens: number | null, contextWindow, percent }`. There is no `usedTokens` or `used`.
  - `ctx.ui.notify(message, type?: "info" | "warning" | "error")`.
- **Prefix stability:** Never append volatile content to `systemPrompt`. Volatile content goes in the `message` return field or a tool result. (`pi-rules/performance.md`, Context Engineering Kernel §1)
- **Never write outside the project directory.** (`pi-rules/AGENTS.md` 鐵律 §3)
- **Test commands:**
  - Python: `python -m unittest discover -s tests -v`
  - TypeScript: `node --test pi-extensions/async-exec-bridge/`

## Starting Parameters (from spec)

| Constant | Value |
|---|---|
| `JOB_TIMEOUT_MS` | `30 * 60 * 1000` |
| `MAX_CONCURRENT_JOBS` | `3` |
| `ENVELOPE_TAIL_BYTES` | `4 * 1024` |
| `CAPTURE_MAX_BYTES` | `8 * 1024 * 1024` |
| `HEARTBEAT_INTERVAL_MS` | `10 * 1000` |
| `LEASE_STALE_MS` | `60 * 1000` |

## File Structure

| File | Responsibility |
|---|---|
| `pi-extensions/async-exec-bridge/package.json` | ESM manifest, `pi-harness.root` placeholder |
| `pi-extensions/async-exec-bridge/constants.ts` | The table above, one export each |
| `pi-extensions/async-exec-bridge/paths.ts` | Resolve run directory and per-job file paths |
| `pi-extensions/async-exec-bridge/jobs.ts` | Job record shape, atomic write, read-all, reconcile |
| `pi-extensions/async-exec-bridge/lease.ts` | GPU lease: acquire, release, heartbeat, staleness, reap |
| `pi-extensions/async-exec-bridge/envelope.ts` | Bounded result envelope |
| `pi-extensions/async-exec-bridge/preflight.ts` | The four dispatch gates |
| `pi-extensions/async-exec-bridge/state-block.ts` | Deliberation state block text |
| `pi-extensions/async-exec-bridge/index.ts` | Pi wiring only: three tools, lifecycle hooks, notification |
| `tests/test_async_exec_bridge.py` | Contract + wiring assertions (repo's existing pattern) |
| `scripts/restore.py` | Three edits to register the bridge |
| `pi-extensions/bridge-manifest.json` | One new entry |

Unit tests sit beside their module as `<name>.test.ts`.

---

### Task 1: Bridge skeleton and registration

**Files:**
- Create: `pi-extensions/async-exec-bridge/package.json`
- Create: `pi-extensions/async-exec-bridge/index.ts`
- Modify: `pi-extensions/bridge-manifest.json`
- Modify: `scripts/restore.py` (three sites)
- Modify: `.gitignore` (the run directory holds live job state, not source)
- Test: `tests/test_async_exec_bridge.py`

**Interfaces:**
- Consumes: nothing.
- Produces: a loadable extension named `async-exec-bridge`; `index.ts` exports `default function (pi: ExtensionAPI): void`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_async_exec_bridge.py`:

```python
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class TestAsyncExecBridgeSkeleton(unittest.TestCase):
    """The bridge dispatches long-running work, lets the agent stop, and wakes
    it when the work finishes. See
    docs/superpowers/specs/2026-08-03-async-resumable-execution-design.md"""

    IDX = "pi-extensions/async-exec-bridge/index.ts"
    PKG = "pi-extensions/async-exec-bridge/package.json"

    def test_package_is_esm_with_harness_root(self):
        pkg = read(self.PKG)
        self.assertIn('"type": "module"', pkg)
        self.assertIn("pi-harness", pkg)

    def test_index_exports_default_extension(self):
        c = read(self.IDX)
        self.assertIn("export default function", c)

    def test_listed_in_bridge_manifest(self):
        m = json.loads(read("pi-extensions/bridge-manifest.json"))
        names = [b["name"] for b in m["bridges"]]
        self.assertIn("async-exec-bridge", names)

    def test_run_directory_is_gitignored(self):
        """Job records and captured output are live state, not source. Without
        this every dispatch dirties `git status`."""
        self.assertIn(".pi/", read(".gitignore"))


class TestAsyncExecBridgeRestoreWiring(unittest.TestCase):
    def test_bridge_registered_and_managed(self):
        c = read("scripts/restore.py")
        self.assertIn('pi_extensions_root, "async-exec-bridge"', c)
        self.assertEqual(c.count('"async-exec-bridge"'), 3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -v -k AsyncExecBridge`
Expected: FAIL — `FileNotFoundError` for `package.json`.

- [ ] **Step 3: Write minimal implementation**

Create `pi-extensions/async-exec-bridge/package.json`:

```json
{
  "name": "async-exec-bridge",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "main": "index.ts",
  "pi-harness": {
    "root": "TODO_SET_BY_RESTORE"
  }
}
```

Create `pi-extensions/async-exec-bridge/index.ts`:

```typescript
/**
 * Async Exec Bridge
 *
 * Dispatches long-running work without blocking the agent, and wakes the agent
 * when that work finishes. Compaction continuation is already handled by
 * compact-continuation-bridge; this covers long programs and subagents.
 *
 * Verified platform facts this depends on:
 *   - an extension's event loop survives an idle agent, and detached
 *     setTimeout fires on time;
 *   - pi.sendMessage(msg, { triggerTurn: true, deliverAs: "followUp" }) wakes
 *     an idle agent.
 * See docs/retro/2026-08-03-absence-is-not-impossibility.md
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  void pi;
}
```

In `pi-extensions/bridge-manifest.json`, add to the `bridges` array:

```json
{
  "name": "async-exec-bridge",
  "entry": "pi-extensions/async-exec-bridge/index.ts",
  "version": "1.0.0",
  "description": "Background execution with automatic resumption"
}
```

In `scripts/restore.py`, make three edits mirroring `compact-continuation-bridge`:

1. Near the existing `profile_extensions.append(...)` for `compact-continuation-bridge` (around line 1014), add:

```python
    # async-exec-bridge: dispatches long-running work without blocking the
    # agent, and wakes it with a followUp + triggerTurn message on completion.
    profile_extensions.append(os.path.join(pi_extensions_root, "async-exec-bridge").replace("\\", "/"))
```

2. Add `"async-exec-bridge"` to the `internal_bridge_names` list (around line 1027).

3. Add `"async-exec-bridge"` to the bridge delete loop list (around line 1202).

In `.gitignore`, add the run directory:

```
.pi/
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -v -k AsyncExecBridge`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add pi-extensions/async-exec-bridge pi-extensions/bridge-manifest.json scripts/restore.py tests/test_async_exec_bridge.py .gitignore
git commit -m "feat(async-exec): add bridge skeleton and registration"
```

---

### Task 2: Constants and path resolution

**Files:**
- Create: `pi-extensions/async-exec-bridge/constants.ts`
- Create: `pi-extensions/async-exec-bridge/paths.ts`
- Test: `pi-extensions/async-exec-bridge/paths.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `constants.ts`: `JOB_TIMEOUT_MS`, `MAX_CONCURRENT_JOBS`, `ENVELOPE_TAIL_BYTES`, `CAPTURE_MAX_BYTES`, `HEARTBEAT_INTERVAL_MS`, `LEASE_STALE_MS` — all `number`.
  - `paths.ts`: `runDir(cwd: string): string`, `jobFile(cwd: string, id: string): string`, `outFile(cwd: string, id: string): string`, `leaseFile(cwd: string): string`.

- [ ] **Step 1: Write the failing test**

Create `pi-extensions/async-exec-bridge/paths.test.ts`:

```typescript
import { test } from "node:test";
import assert from "node:assert/strict";
import { runDir, jobFile, outFile, leaseFile } from "./paths.ts";

test("all artefacts live under the project run directory", () => {
  const cwd = "/tmp/proj";
  assert.equal(runDir(cwd), "/tmp/proj/.pi/async-exec");
  assert.equal(jobFile(cwd, "a3f1"), "/tmp/proj/.pi/async-exec/job-a3f1.json");
  assert.equal(outFile(cwd, "a3f1"), "/tmp/proj/.pi/async-exec/job-a3f1.out");
  assert.equal(leaseFile(cwd), "/tmp/proj/.pi/async-exec/gpu.lease");
});

test("paths are normalised to forward slashes", () => {
  assert.equal(runDir("C:\\proj"), "C:/proj/.pi/async-exec");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test pi-extensions/async-exec-bridge/paths.test.ts`
Expected: FAIL — cannot find module `./paths.ts`.

- [ ] **Step 3: Write minimal implementation**

Create `pi-extensions/async-exec-bridge/constants.ts`:

```typescript
export const JOB_TIMEOUT_MS = 30 * 60 * 1000;
export const MAX_CONCURRENT_JOBS = 3;
/** Bytes of tail injected into context. NOT the capture cap — 8 MiB of output
 *  in the prompt would cost minutes of prefill on a local model. */
export const ENVELOPE_TAIL_BYTES = 4 * 1024;
/** Bytes kept on disk. Never injected. */
export const CAPTURE_MAX_BYTES = 8 * 1024 * 1024;
export const HEARTBEAT_INTERVAL_MS = 10 * 1000;
export const LEASE_STALE_MS = 60 * 1000;
```

Create `pi-extensions/async-exec-bridge/paths.ts`:

```typescript
function norm(p: string): string {
  return p.replace(/\\/g, "/").replace(/\/+$/, "");
}

export function runDir(cwd: string): string {
  return `${norm(cwd)}/.pi/async-exec`;
}

export function jobFile(cwd: string, id: string): string {
  return `${runDir(cwd)}/job-${id}.json`;
}

export function outFile(cwd: string, id: string): string {
  return `${runDir(cwd)}/job-${id}.out`;
}

export function leaseFile(cwd: string): string {
  return `${runDir(cwd)}/gpu.lease`;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test pi-extensions/async-exec-bridge/paths.test.ts`
Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add pi-extensions/async-exec-bridge/constants.ts pi-extensions/async-exec-bridge/paths.ts pi-extensions/async-exec-bridge/paths.test.ts
git commit -m "feat(async-exec): add constants and path resolution"
```

---

### Task 3: Job store with atomic writes and reconcile

**Files:**
- Create: `pi-extensions/async-exec-bridge/jobs.ts`
- Test: `pi-extensions/async-exec-bridge/jobs.test.ts`

**Interfaces:**
- Consumes: `paths.ts` (`runDir`, `jobFile`).
- Produces:
  - `type JobState = "running" | "done" | "failed" | "timeout" | "cancelled" | "orphaned"`
  - `type LocalModel = "none" | "shared" | "exclusive"`
  - `interface JobRecord { id: string; label: string; cmd: string; cwd: string; localModel: LocalModel; pid: number | null; state: JobState; startedAt: number; endedAt: number | null; exitCode: number | null; outPath: string; acknowledged: boolean; }`
  - `writeJob(cwd: string, job: JobRecord): void` — atomic
  - `readJobs(cwd: string): JobRecord[]`
  - `reconcile(jobs: JobRecord[], isAlive: (pid: number) => boolean): JobRecord[]` — pure; returns only the records that changed

- [ ] **Step 1: Write the failing test**

Create `pi-extensions/async-exec-bridge/jobs.test.ts`:

```typescript
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { writeJob, readJobs, reconcile, type JobRecord } from "./jobs.ts";

function sample(over: Partial<JobRecord> = {}): JobRecord {
  return {
    id: "a3f1",
    label: "run tests",
    cmd: "npm test",
    cwd: "/tmp/proj",
    localModel: "none",
    pid: 1234,
    state: "running",
    startedAt: 1000,
    endedAt: null,
    exitCode: null,
    outPath: "/tmp/proj/.pi/async-exec/job-a3f1.out",
    acknowledged: false,
    ...over,
  };
}

test("write then read round-trips a job record", () => {
  const cwd = mkdtempSync(join(tmpdir(), "aeb-"));
  writeJob(cwd, sample());
  const jobs = readJobs(cwd);
  assert.equal(jobs.length, 1);
  assert.equal(jobs[0].id, "a3f1");
  assert.equal(jobs[0].state, "running");
});

test("write leaves no temp files behind", () => {
  const cwd = mkdtempSync(join(tmpdir(), "aeb-"));
  writeJob(cwd, sample());
  const files = readdirSync(`${cwd.replace(/\\/g, "/")}/.pi/async-exec`);
  assert.deepEqual(files.filter((f) => f.includes(".tmp")), []);
});

test("readJobs on a missing directory returns empty, not a throw", () => {
  const cwd = mkdtempSync(join(tmpdir(), "aeb-"));
  assert.deepEqual(readJobs(cwd), []);
});

test("reconcile marks running jobs with dead pids as orphaned", () => {
  const jobs = [sample({ id: "dead", pid: 999 }), sample({ id: "live", pid: 111 })];
  const changed = reconcile(jobs, (pid) => pid === 111);
  assert.equal(changed.length, 1);
  assert.equal(changed[0].id, "dead");
  assert.equal(changed[0].state, "orphaned");
});

test("reconcile leaves finished jobs alone", () => {
  const jobs = [sample({ id: "done", state: "done", pid: 999, exitCode: 0 })];
  assert.deepEqual(reconcile(jobs, () => false), []);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test pi-extensions/async-exec-bridge/jobs.test.ts`
Expected: FAIL — cannot find module `./jobs.ts`.

- [ ] **Step 3: Write minimal implementation**

Create `pi-extensions/async-exec-bridge/jobs.ts`:

```typescript
import { mkdirSync, readdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { jobFile, runDir } from "./paths.ts";

export type JobState = "running" | "done" | "failed" | "timeout" | "cancelled" | "orphaned";
export type LocalModel = "none" | "shared" | "exclusive";

export interface JobRecord {
  id: string;
  label: string;
  cmd: string;
  cwd: string;
  localModel: LocalModel;
  pid: number | null;
  state: JobState;
  startedAt: number;
  endedAt: number | null;
  exitCode: number | null;
  outPath: string;
  /** True once its envelope has been delivered to the agent. Survives crashes
   *  so a completed-but-unreported job is not silently lost. */
  acknowledged: boolean;
}

/** Write via temp + rename so a crash mid-write cannot leave a partial record. */
export function writeJob(cwd: string, job: JobRecord): void {
  const dir = runDir(cwd);
  mkdirSync(dir, { recursive: true });
  const target = jobFile(cwd, job.id);
  const tmp = `${target}.tmp`;
  writeFileSync(tmp, JSON.stringify(job, null, 2), "utf-8");
  renameSync(tmp, target);
}

export function readJobs(cwd: string): JobRecord[] {
  const dir = runDir(cwd);
  let names: string[];
  try {
    names = readdirSync(dir);
  } catch {
    return [];
  }
  const out: JobRecord[] = [];
  for (const n of names) {
    if (!n.startsWith("job-") || !n.endsWith(".json")) continue;
    try {
      out.push(JSON.parse(readFileSync(`${dir}/${n}`, "utf-8")) as JobRecord);
    } catch {
      // A partial or corrupt record is skipped rather than crashing startup.
    }
  }
  return out;
}

/** Pure. Returns only the records whose state changed. */
export function reconcile(jobs: JobRecord[], isAlive: (pid: number) => boolean): JobRecord[] {
  const changed: JobRecord[] = [];
  for (const j of jobs) {
    if (j.state !== "running") continue;
    if (j.pid !== null && isAlive(j.pid)) continue;
    changed.push({ ...j, state: "orphaned", endedAt: Date.now() });
  }
  return changed;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test pi-extensions/async-exec-bridge/jobs.test.ts`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add pi-extensions/async-exec-bridge/jobs.ts pi-extensions/async-exec-bridge/jobs.test.ts
git commit -m "feat(async-exec): add job store with atomic writes and reconcile"
```

---

### Task 4: GPU lease with heartbeat and reaping

**Files:**
- Create: `pi-extensions/async-exec-bridge/lease.ts`
- Test: `pi-extensions/async-exec-bridge/lease.test.ts`

**Interfaces:**
- Consumes: `paths.ts` (`leaseFile`, `runDir`), `constants.ts` (`LEASE_STALE_MS`).
- Produces:
  - `interface Lease { holderPid: number; jobId: string; beatAt: number; }`
  - `isStale(lease: Lease, now: number, isAlive: (pid: number) => boolean): boolean` — pure
  - `readLease(cwd: string): Lease | null`
  - `acquire(cwd: string, jobId: string, pid: number, now: number, isAlive: (pid: number) => boolean): boolean`
  - `beat(cwd: string, now: number): void`
  - `release(cwd: string, jobId: string): void`

- [ ] **Step 1: Write the failing test**

Create `pi-extensions/async-exec-bridge/lease.test.ts`:

```typescript
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { acquire, beat, isStale, readLease, release } from "./lease.ts";

const alive = () => true;
const dead = () => false;

test("a fresh lease held by a live process is not stale", () => {
  assert.equal(isStale({ holderPid: 1, jobId: "x", beatAt: 1000 }, 1000, alive), false);
});

test("a lease is stale once the heartbeat is older than the threshold", () => {
  assert.equal(isStale({ holderPid: 1, jobId: "x", beatAt: 0 }, 61_000, alive), true);
  assert.equal(isStale({ holderPid: 1, jobId: "x", beatAt: 0 }, 59_000, alive), false);
});

test("a lease whose holder is gone is stale regardless of heartbeat", () => {
  assert.equal(isStale({ holderPid: 1, jobId: "x", beatAt: 1000 }, 1000, dead), true);
});

test("acquire succeeds on a clean directory", () => {
  const cwd = mkdtempSync(join(tmpdir(), "aeb-"));
  assert.equal(acquire(cwd, "j1", 100, 1000, alive), true);
  assert.equal(readLease(cwd)?.jobId, "j1");
});

test("acquire fails while a live lease is held", () => {
  const cwd = mkdtempSync(join(tmpdir(), "aeb-"));
  acquire(cwd, "j1", 100, 1000, alive);
  assert.equal(acquire(cwd, "j2", 200, 1000, alive), false);
});

test("acquire reaps a stale lease and takes it", () => {
  const cwd = mkdtempSync(join(tmpdir(), "aeb-"));
  acquire(cwd, "j1", 100, 1000, alive);
  assert.equal(acquire(cwd, "j2", 200, 1000, dead), true);
  assert.equal(readLease(cwd)?.jobId, "j2");
});

test("release only clears the lease held by the given job", () => {
  const cwd = mkdtempSync(join(tmpdir(), "aeb-"));
  acquire(cwd, "j1", 100, 1000, alive);
  release(cwd, "someone-else");
  assert.equal(readLease(cwd)?.jobId, "j1");
  release(cwd, "j1");
  assert.equal(readLease(cwd), null);
});

test("beat refreshes the heartbeat", () => {
  const cwd = mkdtempSync(join(tmpdir(), "aeb-"));
  acquire(cwd, "j1", 100, 1000, alive);
  beat(cwd, 5000);
  assert.equal(readLease(cwd)?.beatAt, 5000);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test pi-extensions/async-exec-bridge/lease.test.ts`
Expected: FAIL — cannot find module `./lease.ts`.

- [ ] **Step 3: Write minimal implementation**

Create `pi-extensions/async-exec-bridge/lease.ts`:

```typescript
import { mkdirSync, readFileSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { leaseFile, runDir } from "./paths.ts";
import { LEASE_STALE_MS } from "./constants.ts";

export interface Lease {
  holderPid: number;
  jobId: string;
  beatAt: number;
}

/** Pure. A lease is dead if its holder is gone OR its heartbeat has aged out.
 *  Both checks matter: an orphaned process can hold a resource for hours while
 *  looking perfectly alive to a naive check. */
export function isStale(lease: Lease, now: number, isAlive: (pid: number) => boolean): boolean {
  if (!isAlive(lease.holderPid)) return true;
  return now - lease.beatAt > LEASE_STALE_MS;
}

export function readLease(cwd: string): Lease | null {
  try {
    return JSON.parse(readFileSync(leaseFile(cwd), "utf-8")) as Lease;
  } catch {
    return null;
  }
}

function put(cwd: string, lease: Lease): void {
  mkdirSync(runDir(cwd), { recursive: true });
  const target = leaseFile(cwd);
  const tmp = `${target}.tmp`;
  writeFileSync(tmp, JSON.stringify(lease), "utf-8");
  renameSync(tmp, target);
}

export function acquire(
  cwd: string,
  jobId: string,
  pid: number,
  now: number,
  isAlive: (pid: number) => boolean,
): boolean {
  const held = readLease(cwd);
  if (held && !isStale(held, now, isAlive)) return false;
  put(cwd, { holderPid: pid, jobId, beatAt: now });
  return true;
}

export function beat(cwd: string, now: number): void {
  const held = readLease(cwd);
  if (!held) return;
  put(cwd, { ...held, beatAt: now });
}

export function release(cwd: string, jobId: string): void {
  const held = readLease(cwd);
  if (!held || held.jobId !== jobId) return;
  try {
    rmSync(leaseFile(cwd));
  } catch {
    // Already gone.
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test pi-extensions/async-exec-bridge/lease.test.ts`
Expected: PASS, 8 tests.

- [ ] **Step 5: Commit**

```bash
git add pi-extensions/async-exec-bridge/lease.ts pi-extensions/async-exec-bridge/lease.test.ts
git commit -m "feat(async-exec): add GPU lease with heartbeat and reaping"
```

---

### Task 5: Bounded result envelope

**Files:**
- Create: `pi-extensions/async-exec-bridge/envelope.ts`
- Test: `pi-extensions/async-exec-bridge/envelope.test.ts`

**Interfaces:**
- Consumes: `constants.ts` (`ENVELOPE_TAIL_BYTES`), `jobs.ts` (`JobRecord`).
- Produces:
  - `tailBytes(s: string, max: number): string` — pure
  - `buildEnvelope(jobs: JobRecord[], tails: Map<string, string>): string` — pure

- [ ] **Step 1: Write the failing test**

Create `pi-extensions/async-exec-bridge/envelope.test.ts`:

```typescript
import { test } from "node:test";
import assert from "node:assert/strict";
import { buildEnvelope, tailBytes } from "./envelope.ts";
import type { JobRecord } from "./jobs.ts";

function job(over: Partial<JobRecord> = {}): JobRecord {
  return {
    id: "a3f1", label: "run tests", cmd: "npm test", cwd: "/tmp/p",
    localModel: "none", pid: 1, state: "done", startedAt: 0, endedAt: 5000,
    exitCode: 0, outPath: "/tmp/p/.pi/async-exec/job-a3f1.out",
    acknowledged: false, ...over,
  };
}

test("tailBytes keeps the end, not the start", () => {
  assert.equal(tailBytes("abcdefghij", 4), "ghij");
});

test("tailBytes leaves short input untouched", () => {
  assert.equal(tailBytes("abc", 10), "abc");
});

test("envelope names the job, its outcome and its duration", () => {
  const text = buildEnvelope([job()], new Map([["a3f1", "ok"]]));
  assert.match(text, /a3f1/);
  assert.match(text, /run tests/);
  assert.match(text, /exit=0/);
  assert.match(text, /5\.0s/);
});

test("envelope always carries the on-disk path so full output stays reachable", () => {
  const text = buildEnvelope([job()], new Map());
  assert.match(text, /job-a3f1\.out/);
});

test("several completions coalesce into one envelope", () => {
  const text = buildEnvelope(
    [job({ id: "one" }), job({ id: "two", state: "failed", exitCode: 1 })],
    new Map(),
  );
  assert.match(text, /one/);
  assert.match(text, /two/);
  assert.equal(text.split("[bg] job").length - 1, 2);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test pi-extensions/async-exec-bridge/envelope.test.ts`
Expected: FAIL — cannot find module `./envelope.ts`.

- [ ] **Step 3: Write minimal implementation**

Create `pi-extensions/async-exec-bridge/envelope.ts`:

```typescript
import { ENVELOPE_TAIL_BYTES } from "./constants.ts";
import type { JobRecord } from "./jobs.ts";

/** Keep the end of the output — the failure is almost always at the tail. */
export function tailBytes(s: string, max: number): string {
  if (s.length <= max) return s;
  return s.slice(s.length - max);
}

export function buildEnvelope(jobs: JobRecord[], tails: Map<string, string>): string {
  const lines: string[] = [
    "[async-exec] Background work finished. Continue from where you stopped;" +
      " if nothing is outstanding, say so and stop rather than inventing work.",
  ];
  for (const j of jobs) {
    const secs = j.endedAt === null ? 0 : (j.endedAt - j.startedAt) / 1000;
    lines.push(
      `[bg] job ${j.id} · "${j.label}" · ${j.state} · exit=${j.exitCode ?? "n/a"} · ${secs.toFixed(1)}s`,
    );
    lines.push(`     full output: ${j.outPath}`);
    const tail = tails.get(j.id);
    if (tail) {
      lines.push(`     tail:\n${tailBytes(tail, ENVELOPE_TAIL_BYTES)}`);
    }
  }
  return lines.join("\n");
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test pi-extensions/async-exec-bridge/envelope.test.ts`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add pi-extensions/async-exec-bridge/envelope.ts pi-extensions/async-exec-bridge/envelope.test.ts
git commit -m "feat(async-exec): add bounded result envelope"
```

---

### Task 6: Preflight gates

**Files:**
- Create: `pi-extensions/async-exec-bridge/preflight.ts`
- Test: `pi-extensions/async-exec-bridge/preflight.test.ts`

**Interfaces:**
- Consumes: `constants.ts` (`MAX_CONCURRENT_JOBS`), `jobs.ts` (`JobRecord`, `LocalModel`).
- Produces:
  - `interface PreflightInput { jobs: JobRecord[]; cmd: string; cwd: string; localModel: LocalModel; leaseHeld: boolean; gpuCommittedGiB?: number; cleanBaselineGiB?: number; }` — the GPU figures are **optional**, because v1 has no probe. Absent means "not measured", and the exclusive gate refuses on that.
  - `type PreflightResult = { ok: true } | { ok: false; reason: string } | { ok: "duplicate"; id: string }`
  - `preflight(i: PreflightInput): PreflightResult` — pure

- [ ] **Step 1: Write the failing test**

Create `pi-extensions/async-exec-bridge/preflight.test.ts`:

```typescript
import { test } from "node:test";
import assert from "node:assert/strict";
import { preflight, type PreflightInput } from "./preflight.ts";
import type { JobRecord } from "./jobs.ts";

function running(id: string, cmd: string, cwd = "/tmp/p"): JobRecord {
  return {
    id, label: id, cmd, cwd, localModel: "none", pid: 1, state: "running",
    startedAt: 0, endedAt: null, exitCode: null, outPath: "", acknowledged: false,
  };
}

function input(over: Partial<PreflightInput> = {}): PreflightInput {
  return {
    jobs: [], cmd: "npm test", cwd: "/tmp/p", localModel: "none",
    leaseHeld: false, gpuCommittedGiB: 2.0, cleanBaselineGiB: 2.5, ...over,
  };
}

test("a clean dispatch passes", () => {
  assert.deepEqual(preflight(input()), { ok: true });
});

test("an identical running command is reported as a duplicate, not dispatched twice", () => {
  const r = preflight(input({ jobs: [running("old", "npm test")] }));
  assert.deepEqual(r, { ok: "duplicate", id: "old" });
});

test("the same command in a different directory is not a duplicate", () => {
  const r = preflight(input({ jobs: [running("old", "npm test", "/tmp/other")] }));
  assert.deepEqual(r, { ok: true });
});

test("dispatch is refused once the concurrency cap is reached", () => {
  const jobs = [running("a", "x"), running("b", "y"), running("c", "z")];
  const r = preflight(input({ jobs }));
  assert.equal(r.ok, false);
  assert.match((r as { reason: string }).reason, /concurrent/i);
});

test("exclusive is refused while the lease is held", () => {
  const r = preflight(input({ localModel: "exclusive", leaseHeld: true }));
  assert.equal(r.ok, false);
  assert.match((r as { reason: string }).reason, /lease/i);
});

test("exclusive is refused while a model is resident, and says what to do instead", () => {
  const r = preflight(input({ localModel: "exclusive", gpuCommittedGiB: 85.6 }));
  assert.equal(r.ok, false);
  const reason = (r as { reason: string }).reason;
  assert.match(reason, /resident/i);
  assert.match(reason, /shared/);
});

test("exclusive passes on an idle GPU with no lease", () => {
  assert.deepEqual(
    preflight(input({ localModel: "exclusive", gpuCommittedGiB: 2.1 })),
    { ok: true },
  );
});

test("shared is never blocked by GPU residency — it uses the running server", () => {
  assert.deepEqual(
    preflight(input({ localModel: "shared", gpuCommittedGiB: 85.6 })),
    { ok: true },
  );
});

test("exclusive is refused when nothing measured the GPU at all", () => {
  // v1 ships no probe. An unmeasured GPU must read as "cannot verify", never as
  // "nothing resident" — the optimistic reading is exactly the one that puts two
  // large models in the same carve.
  const r = preflight(input({
    localModel: "exclusive",
    gpuCommittedGiB: undefined,
    cleanBaselineGiB: undefined,
  }));
  assert.equal(r.ok, false);
  assert.match((r as { reason: string }).reason, /not probed|no .*probe/i);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test pi-extensions/async-exec-bridge/preflight.test.ts`
Expected: FAIL — cannot find module `./preflight.ts`.

- [ ] **Step 3: Write minimal implementation**

Create `pi-extensions/async-exec-bridge/preflight.ts`:

```typescript
import { MAX_CONCURRENT_JOBS } from "./constants.ts";
import type { JobRecord, LocalModel } from "./jobs.ts";

export interface PreflightInput {
  jobs: JobRecord[];
  cmd: string;
  cwd: string;
  localModel: LocalModel;
  leaseHeld: boolean;
  /** Committed adapter memory, not reported free memory: the reported figure
   *  counts shared system memory and would wave a doomed job through.
   *  Optional because v1 has no probe — undefined means "not measured", which
   *  the exclusive gate treats as a refusal, not as an idle GPU. */
  gpuCommittedGiB?: number;
  cleanBaselineGiB?: number;
}

export type PreflightResult =
  | { ok: true }
  | { ok: false; reason: string }
  | { ok: "duplicate"; id: string };

export function preflight(i: PreflightInput): PreflightResult {
  const dup = i.jobs.find((j) => j.state === "running" && j.cmd === i.cmd && j.cwd === i.cwd);
  if (dup) return { ok: "duplicate", id: dup.id };

  const running = i.jobs.filter((j) => j.state === "running").length;
  if (running >= MAX_CONCURRENT_JOBS) {
    return { ok: false, reason: `at the concurrent job limit (${MAX_CONCURRENT_JOBS}); park until one finishes` };
  }

  if (i.localModel === "exclusive") {
    if (i.leaseHeld) {
      return { ok: false, reason: "the GPU lease is held by another job" };
    }
    if (i.gpuCommittedGiB === undefined || i.cleanBaselineGiB === undefined) {
      return {
        ok: false,
        reason:
          "GPU residency is not probed, so it cannot be verified that a second local model would fit. " +
          'Use localModel "shared" to reuse the running server, or use a cloud model.',
      };
    }
    if (i.gpuCommittedGiB > i.cleanBaselineGiB) {
      return {
        ok: false,
        reason:
          `a local model is resident (${i.gpuCommittedGiB.toFixed(1)} GiB committed vs ` +
          `${i.cleanBaselineGiB.toFixed(1)} GiB idle baseline); a second one will not fit. ` +
          `Use localModel "shared" to reuse the running server, use a cloud model, ` +
          `or stop the main server first.`,
      };
    }
  }

  return { ok: true };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test pi-extensions/async-exec-bridge/preflight.test.ts`
Expected: PASS, 9 tests.

- [ ] **Step 5: Commit**

```bash
git add pi-extensions/async-exec-bridge/preflight.ts pi-extensions/async-exec-bridge/preflight.test.ts
git commit -m "feat(async-exec): add preflight dispatch gates"
```

---

### Task 7: Deliberation state block

**Files:**
- Create: `pi-extensions/async-exec-bridge/state-block.ts`
- Test: `pi-extensions/async-exec-bridge/state-block.test.ts`

**Interfaces:**
- Consumes: `jobs.ts` (`JobRecord`).
- Produces:
  - `interface StateInput { dispatched: JobRecord; running: JobRecord[]; gpuCommittedGiB: number; carveGiB: number; contextTokens: number; serverSlots: number; }`
  - `stateBlock(i: StateInput): string` — pure

- [ ] **Step 1: Write the failing test**

Create `pi-extensions/async-exec-bridge/state-block.test.ts`:

```typescript
import { test } from "node:test";
import assert from "node:assert/strict";
import { stateBlock, type StateInput } from "./state-block.ts";
import type { JobRecord } from "./jobs.ts";

function job(over: Partial<JobRecord> = {}): JobRecord {
  return {
    id: "a3f1", label: "run integration suite", cmd: "npm test", cwd: "/tmp/p",
    localModel: "none", pid: 1, state: "running", startedAt: 0, endedAt: null,
    exitCode: null, outPath: "", acknowledged: false, ...over,
  };
}

function input(over: Partial<StateInput> = {}): StateInput {
  return {
    dispatched: job(), running: [job()], gpuCommittedGiB: 85.6, carveGiB: 96,
    contextTokens: 18_000, serverSlots: 1, ...over,
  };
}

test("the block states the job, the resources and the context depth", () => {
  const s = stateBlock(input());
  assert.match(s, /a3f1/);
  assert.match(s, /run integration suite/);
  assert.match(s, /localModel=none/);
  assert.match(s, /18K/);
});

test("it asks for a one-line PARK or CONTINUE decision", () => {
  const s = stateBlock(input());
  assert.match(s, /PARK/);
  assert.match(s, /CONTINUE/);
});

test("with a single server slot a shared job is described as blocking, not slowing", () => {
  const s = stateBlock(input({ dispatched: job({ localModel: "shared" }), serverSlots: 1 }));
  assert.match(s, /block/i);
  assert.doesNotMatch(s, /slows your own decode/i);
});

test("with no GPU probe the block says so rather than printing a made-up number", () => {
  const s = stateBlock({ ...input(), gpuCommittedGiB: undefined, carveGiB: undefined });
  assert.match(s, /not probed/);
  assert.doesNotMatch(s, /headroom/);
});

test("with several slots a shared job only slows the agent", () => {
  const s = stateBlock(input({ dispatched: job({ localModel: "shared" }), serverSlots: 4 }));
  assert.match(s, /slow/i);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test pi-extensions/async-exec-bridge/state-block.test.ts`
Expected: FAIL — cannot find module `./state-block.ts`.

- [ ] **Step 3: Write minimal implementation**

Create `pi-extensions/async-exec-bridge/state-block.ts`:

```typescript
import type { JobRecord } from "./jobs.ts";

export interface StateInput {
  dispatched: JobRecord;
  running: JobRecord[];
  /** Omit when there is no live probe. Printing a placeholder would tell the
   *  model it has 93 GiB of headroom while a resident model is using 85 - and
   *  feeding the deliberation fabricated facts is worse than feeding it none. */
  gpuCommittedGiB?: number;
  carveGiB?: number;
  contextTokens: number;
  /** llama-server slot count. At 1, a "shared" job serialises at the server:
   *  the agent's own decode stops rather than merely slowing. */
  serverSlots: number;
}

export function stateBlock(i: StateInput): string {
  const d = i.dispatched;
  const depthK = `${Math.round(i.contextTokens / 1000)}K`;

  const lines = [
    `[bg] dispatched job ${d.id} · "${d.label}" · localModel=${d.localModel}`,
  ];
  if (i.gpuCommittedGiB !== undefined && i.carveGiB !== undefined) {
    const headroom = (i.carveGiB - i.gpuCommittedGiB).toFixed(1);
    lines.push(
      `[bg] running: ${i.running.length}    GPU committed: ${i.gpuCommittedGiB.toFixed(1)} GiB / ${i.carveGiB} GiB carve (headroom ${headroom} GiB)`,
    );
  } else {
    lines.push(`[bg] running: ${i.running.length}    GPU state: not probed in v1`);
  }
  lines.push(
    `[bg] your context depth: ~${depthK} — prefill and decode both get slower as this grows`,
  );

  if (d.localModel === "shared") {
    lines.push(
      i.serverSlots <= 1
        ? `[bg] WARNING: the model server has ${i.serverSlots} slot, so this job will BLOCK your own decode until it finishes, not merely slow it`
        : `[bg] note: this job shares the model server (${i.serverSlots} slots), so it will slow your own decode`,
    );
  }

  lines.push(
    "Decide in one line: PARK (stop issuing tool calls and end this turn; you will be woken when the job finishes) or CONTINUE (say what you will do meanwhile).",
  );
  return lines.join("\n");
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test pi-extensions/async-exec-bridge/state-block.test.ts`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add pi-extensions/async-exec-bridge/state-block.ts pi-extensions/async-exec-bridge/state-block.test.ts
git commit -m "feat(async-exec): add deliberation state block"
```

---

### Task 8: Detached spawn, exit-code capture and process-tree kill

> **Already validated on the reference box (2026-08-03).** A detached child does
> survive its parent exiting: the parent called `process.exit(0)` immediately and
> the child still completed six seconds later and wrote its status file. The
> failing case correctly reported exit 3 rather than 0.
>
> That run also found a real bug, which is why the code below differs from the
> obvious version: `stdio: ["ignore", fd, fd]` produced an **empty output file
> every time** on Windows. A detached child does not reliably inherit a file
> descriptor. Shell-level redirection with `stdio: "ignore"` works, and matches
> Node's documented recommendation. Do not "simplify" it back.

**Files:**
- Create: `pi-extensions/async-exec-bridge/spawn.ts`
- Test: `pi-extensions/async-exec-bridge/spawn.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `startDetached(cmd: string, cwd: string, outPath: string, rcPath: string): number | null` — returns the pid, or null if spawn failed
  - `readExitCode(rcPath: string): number | null` — null means the job never finished; **never treat null as success**
  - `isAlive(pid: number): boolean`
  - `killTree(pid: number): void`

- [ ] **Step 1: Write the failing test**

Create `pi-extensions/async-exec-bridge/spawn.test.ts`:

```typescript
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { isAlive, killTree, readExitCode, startDetached } from "./spawn.ts";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

test("a detached job keeps running after the caller returns", async () => {
  const dir = mkdtempSync(join(tmpdir(), "aeb-")).replace(/\\/g, "/");
  const out = `${dir}/out.txt`;
  const pid = startDetached("sleep 2; echo FINISHED", dir, out, `${out}.rc`);
  assert.notEqual(pid, null);
  assert.equal(isAlive(pid as number), true);
  await sleep(3500);
  assert.match(readFileSync(out, "utf-8"), /FINISHED/);
});

test("a failing job reports its real exit code, not success", async () => {
  const dir = mkdtempSync(join(tmpdir(), "aeb-")).replace(/\\/g, "/");
  const out = `${dir}/out.txt`;
  startDetached("exit 3", dir, out, `${out}.rc`);
  await sleep(2000);
  assert.equal(readExitCode(`${out}.rc`), 3);
});

test("an unfinished job has no exit code, and null must not read as success", async () => {
  const dir = mkdtempSync(join(tmpdir(), "aeb-")).replace(/\\/g, "/");
  const out = `${dir}/out.txt`;
  const pid = startDetached("sleep 30", dir, out, `${out}.rc`) as number;
  assert.equal(readExitCode(`${out}.rc`), null);
  killTree(pid);
});

test("isAlive reports false for a pid that cannot exist", () => {
  assert.equal(isAlive(0x7ffffff0), false);
});

test("killTree stops a running job", async () => {
  const dir = mkdtempSync(join(tmpdir(), "aeb-")).replace(/\\/g, "/");
  const pid = startDetached("sleep 30", dir, `${dir}/out.txt`, `${dir}/out.txt.rc`) as number;
  killTree(pid);
  await sleep(1500);
  assert.equal(isAlive(pid), false);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test pi-extensions/async-exec-bridge/spawn.test.ts`
Expected: FAIL — cannot find module `./spawn.ts`.

- [ ] **Step 3: Write minimal implementation**

Create `pi-extensions/async-exec-bridge/spawn.ts`:

```typescript
import { spawn, spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { CAPTURE_MAX_BYTES } from "./constants.ts";

/** Same resolution order as stealth-web-bridge's findShell(). spawn("bash")
 *  relies on the *process* PATH, which on Windows often does not include Git's
 *  bash — that is the "spawn sh ENOENT" that stopped that bridge from ever
 *  cold-starting. Ask the harness first, then known locations, then PATH.
 *  A machine-specific path must never be the only answer. */
function findShell(): string {
  if (process.env.PI_HARNESS_SHELL) return process.env.PI_HARNESS_SHELL;
  try {
    const cfg = JSON.parse(readFileSync(join(homedir(), ".pi", "agent", "settings.json"), "utf-8"));
    if (cfg.shellPath && existsSync(cfg.shellPath)) return cfg.shellPath;
  } catch {
    // No harness settings; fall through.
  }
  for (const c of [
    "C:\\Program Files\\Git\\bin\\bash.exe",
    "C:\\Program Files\\Git\\usr\\bin\\bash.exe",
    "C:\\Program Files (x86)\\Git\\bin\\bash.exe",
  ]) {
    try {
      if (existsSync(c)) return c;
    } catch {
      // Unreadable candidate; try the next.
    }
  }
  return "bash";
}

const SHELL = findShell();

/** Start a job that outlives the caller. stdout and stderr both go to a file so
 *  nothing depends on this process staying around to drain a pipe. */
export function startDetached(
  cmd: string,
  cwd: string,
  outPath: string,
  rcPath: string,
): number | null {
  // Everything goes through shell-level redirection, and stdio stays "ignore".
  // VERIFIED on Windows: a detached child does NOT reliably receive an
  // inherited file descriptor - stdio: ["ignore", fd, fd] produced an empty
  // output file every time, while the shell redirect below captures both
  // streams. This also matches Node's documented recommendation of pairing
  // detached with stdio: "ignore".
  //
  // head -c caps the capture so a runaway job cannot fill the disk.
  // PIPESTATUS[0] is the command's status, not head's. Caveat: once head has
  // taken its bytes it closes the pipe, so a job that keeps writing past
  // CAPTURE_MAX_BYTES dies of SIGPIPE and PIPESTATUS[0] reads 141 rather than
  // its own code. That is a real misreport, but only for jobs exceeding 8 MiB
  // of output, and 141 is at least not silently 0.
  const wrapped =
    `{ ${cmd} ; } 2>&1 | head -c ${CAPTURE_MAX_BYTES} > ${JSON.stringify(outPath)} ; ` +
    `echo \${PIPESTATUS[0]} > ${JSON.stringify(rcPath)}`;
  const child = spawn(SHELL, ["-lc", wrapped], {
    cwd,
    detached: true,
    stdio: "ignore",
    windowsHide: true,
  });
  if (child.pid === undefined) return null;
  child.unref();
  return child.pid;
}

/** Exit code recorded by the shell wrapper, or null if the job never got that
 *  far (killed, machine lost power). null must NOT be treated as success. */
export function readExitCode(rcPath: string): number | null {
  try {
    const n = Number.parseInt(readFileSync(rcPath, "utf-8").trim(), 10);
    return Number.isNaN(n) ? null : n;
  } catch {
    return null;
  }
}

export function isAlive(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

/** On Windows, killing a pid does NOT kill its children. An orphan left behind
 *  can hold a resource for hours and make the next run look like an unsupported
 *  configuration rather than a busy machine. */
export function killTree(pid: number): void {
  if (process.platform === "win32") {
    spawnSync("taskkill", ["/PID", String(pid), "/T", "/F"], { windowsHide: true });
    return;
  }
  try {
    process.kill(-pid, "SIGKILL");
  } catch {
    try {
      process.kill(pid, "SIGKILL");
    } catch {
      // Already gone.
    }
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test pi-extensions/async-exec-bridge/spawn.test.ts`
Expected: PASS, 5 tests.

If the first test fails because the child dies with its parent, stop and report: the spec's fallback is to have the watcher poll job files from `before_agent_start` instead of relying on a detached child plus in-process timer.

- [ ] **Step 5: Commit**

```bash
git add pi-extensions/async-exec-bridge/spawn.ts pi-extensions/async-exec-bridge/spawn.test.ts
git commit -m "feat(async-exec): add detached spawn with process-tree kill"
```

---

### Task 9: Wire the three tools

**Files:**
- Modify: `pi-extensions/async-exec-bridge/index.ts`
- Modify: `pi-extensions/yes-hooks-bridge/index.ts` — add `bg_start`, `bg_status`, `bg_cancel` to `HARNESS_TOOLS`
- Test: `tests/test_async_exec_bridge.py`

Two repo-wide invariants bite here, both enforced by existing tests:

- `HARNESS_TOOLS` in `yes-hooks-bridge` is a hand-maintained mirror of every tool
  the bridges register. Registering a tool without listing it there puts the
  guard back to telling the model that a real tool does not exist.
- `test_taste_bridge` requires any `index.ts` containing the string `pi-config`
  to resolve the harness root from `package.json`. This bridge does not read
  `pi-config`, so it must not name it — not even in a comment.

**Interfaces:**
- Consumes: every module from Tasks 2-8.
- Produces: tools `bg_start`, `bg_status`, `bg_cancel` registered on the Pi extension API.

`index.ts` is covered by the Python contract tests, not `node --test`: it imports
`@earendil-works/pi-coding-agent` and `typebox`, which resolve under Pi's loader
but not under a bare `node --test` run. That is why every piece of logic worth
unit-testing lives in the sibling modules and this file holds only wiring.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_async_exec_bridge.py`:

```python
class TestAsyncExecBridgeTools(unittest.TestCase):
    IDX = "pi-extensions/async-exec-bridge/index.ts"

    def test_registers_the_three_tools(self):
        """Pi's registerTool takes one object with a `name` field. Asserting on a
        `registerTool("bg_start"` call shape would pin an API that does not
        exist."""
        c = read(self.IDX)
        for tool in ("bg_start", "bg_status", "bg_cancel"):
            self.assertIn(f'name: "{tool}"', c)

    def test_bg_start_declares_its_parameters(self):
        """A tool without a TypeBox `parameters` schema cannot receive arguments,
        so the model would have no way to say what to run."""
        c = read(self.IDX)
        self.assertIn("parameters: Type.Object(", c)
        self.assertIn("cmd:", c)

    def test_dispatch_runs_preflight_before_spawning(self):
        c = read(self.IDX)
        self.assertLess(c.index("preflight("), c.index("startDetached("))

    def test_result_is_written_before_the_wake_attempt(self):
        """Waking can fail and be retried; state cannot. Anchored inside wake()
        because the file header quotes pi.sendMessage in prose, which a
        whole-file index would match first."""
        c = read(self.IDX)
        body = c[c.index("function wake("):]
        self.assertLess(body.index("writeJob("), body.index("pi.sendMessage("))

    def test_pending_results_are_injected_through_before_agent_start(self):
        """session_start is typed ExtensionHandler<SessionStartEvent> with no
        result type — anything returned from it is discarded. before_agent_start
        is the only hook whose result carries a `message`."""
        c = read(self.IDX)
        self.assertIn('pi.on("before_agent_start"', c)
        start = c.index('pi.on("session_start"')
        body = c[start:c.index("pi.on(", start + 10)]
        self.assertNotIn("return { message", body)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -v -k AsyncExecBridgeTools`
Expected: FAIL — `bg_start` not found in `index.ts`.

- [ ] **Step 3: Write minimal implementation**

Replace the body of `pi-extensions/async-exec-bridge/index.ts`:

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { randomBytes } from "node:crypto";
import { readFileSync } from "node:fs";
import { ENVELOPE_TAIL_BYTES, JOB_TIMEOUT_MS } from "./constants.ts";
import { buildEnvelope, tailBytes } from "./envelope.ts";
import { readJobs, reconcile, writeJob, type JobRecord, type LocalModel } from "./jobs.ts";
import { outFile } from "./paths.ts";
import { preflight } from "./preflight.ts";
import { readLease, release } from "./lease.ts";
import { isAlive, killTree, readExitCode, startDetached } from "./spawn.ts";
import { stateBlock } from "./state-block.ts";

export default function (pi: ExtensionAPI) {
  let dead = false;
  const timers = new Set<NodeJS.Timeout>();
  /** Completions that finished while a wake was already in flight. They ride
   *  along in the next envelope instead of each triggering a competing turn. */
  let coalescing: JobRecord[] = [];
  let wakePending = false;

  function envelopeFor(jobs: JobRecord[]): string {
    const tails = new Map<string, string>();
    for (const j of jobs) {
      try {
        tails.set(j.id, tailBytes(readFileSync(j.outPath, "utf-8"), ENVELOPE_TAIL_BYTES));
      } catch {
        // No output captured.
      }
    }
    return buildEnvelope(jobs, tails);
  }

  function wake(cwd: string, ctx: any) {
    const batch = coalescing;
    coalescing = [];
    if (batch.length === 0) {
      wakePending = false;
      return;
    }
    for (const j of batch) writeJob(cwd, { ...j, acknowledged: true });
    // Only ask Pi to start a turn when it is actually idle. Mid-run, followUp
    // alone delivers once it settles; adding triggerTurn would race the turn
    // already in progress.
    const idle = ctx?.isIdle?.() !== false;
    pi.sendMessage(
      { customType: "async-exec", content: envelopeFor(batch), display: true },
      { deliverAs: "followUp", triggerTurn: idle },
    );
    wakePending = false;
  }

  function finish(
    cwd: string,
    ctx: any,
    job: JobRecord,
    state: JobRecord["state"],
    exitCode: number | null,
  ) {
    // State first, always: waking can fail and be retried, state cannot.
    const done: JobRecord = { ...job, state, exitCode, endedAt: Date.now() };
    writeJob(cwd, done);
    release(cwd, job.id);
    if (dead) return;
    coalescing.push(done);
    if (wakePending) return;
    wakePending = true;
    // One tick of slack so simultaneous completions land in a single envelope.
    const t = setTimeout(() => {
      timers.delete(t);
      wake(cwd, ctx);
    }, 250);
    timers.add(t);
  }

  const text = (s: string) => ({ content: [{ type: "text" as const, text: s }] });

  pi.registerTool({
    name: "bg_start",
    label: "Background Start",
    description:
      "Start a long-running command in the background and return immediately. " +
      "You will be woken with the result when it finishes.",
    promptSnippet:
      "bg_start(cmd, label?, localModel?): run a long command in the background; you are woken when it finishes.",
    promptGuidelines: [
      "For a command that will take minutes (builds, full test suites, benchmarks), call bg_start instead of bash — bash blocks this turn until it returns.",
      "After bg_start, decide PARK or CONTINUE in one line. PARK just means issuing no further tool calls this turn; there is no park tool to call.",
      "Use bg_status to check on work you dispatched, and bg_cancel to stop it. A background job keeps running even if this turn is interrupted.",
    ],
    parameters: Type.Object({
      cmd: Type.String({ description: "The shell command to run, e.g. 'npm test'" }),
      label: Type.Optional(Type.String({ description: "Short human-readable name for this job" })),
      localModel: Type.Optional(
        Type.Union([Type.Literal("none"), Type.Literal("shared"), Type.Literal("exclusive")], {
          description:
            "Whether this job touches the local model server: none (default), shared (uses the running server), exclusive (needs to load its own model — refused in v1)",
        }),
      ),
    }),
    async execute(_id, params: any, _signal, _onUpdate, ctx: any) {
      const args = params as { cmd: string; label?: string; localModel?: LocalModel };
      const cwd: string = ctx.cwd;
      const localModel: LocalModel = args.localModel ?? "none";
      // v1 has no live GPU probe, so the residency check cannot be honest.
      // Refuse outright rather than pretend to have checked — a wrong "yes"
      // here means two large models racing for memory.
      if (localModel === "exclusive") {
        return text(
          '[async-exec] refused: localModel "exclusive" is not supported yet — ' +
            "v1 has no live GPU residency probe, so it cannot verify a second model would fit. " +
            'Use "shared" to reuse the running server, or use a cloud model.',
        );
      }
      const jobs = readJobs(cwd);
      // No GPU figures are passed: v1 has no probe. preflight treats their
      // absence as "cannot verify" and refuses exclusive on its own, so the
      // early return above is a clearer duplicate of that gate, not its only
      // enforcement.
      const gate = preflight({
        jobs,
        cmd: args.cmd,
        cwd,
        localModel,
        leaseHeld: readLease(cwd) !== null,
      });
      if (gate.ok === false) return text(`[async-exec] refused: ${gate.reason}`);
      if (gate.ok === "duplicate") return text(`[async-exec] already running as job ${gate.id}`);

      const id = randomBytes(2).toString("hex");
      const out = outFile(cwd, id);
      const rc = `${out}.rc`;
      const pid = startDetached(args.cmd, cwd, out, rc);
      if (pid === null) return text("[async-exec] refused: could not start the process");

      const job: JobRecord = {
        id, label: args.label ?? args.cmd, cmd: args.cmd, cwd, localModel,
        pid, state: "running", startedAt: Date.now(), endedAt: null,
        exitCode: null, outPath: out, acknowledged: false,
      };
      writeJob(cwd, job);

      const poll = setInterval(() => {
        if (dead) return;
        if (isAlive(pid)) {
          if (Date.now() - job.startedAt > JOB_TIMEOUT_MS) {
            killTree(pid);
            clearInterval(poll);
            timers.delete(poll);
            finish(cwd, ctx, job, "timeout", null);
          }
          return;
        }
        clearInterval(poll);
        timers.delete(poll);
        // The pid is gone; the shell wrapper's .rc file is the only witness to
        // how it went. A missing code means it never finished cleanly.
        const code = readExitCode(rc);
        finish(cwd, ctx, job, code === 0 ? "done" : "failed", code);
      }, 2000);
      timers.add(poll);

      // Real depth, not a placeholder: the whole point of showing it is to let
      // the model weigh that continuing makes its own next prefill costlier.
      // ContextUsage is { tokens: number | null, contextWindow, percent } —
      // tokens is null right after compaction, before the next LLM response.
      const usage = ctx.getContextUsage?.();
      return text(
        stateBlock({
          dispatched: job,
          running: readJobs(cwd).filter((j) => j.state === "running"),
          // No GPU fields: v1 has no probe, so they are omitted rather than faked.
          contextTokens: usage?.tokens ?? 0,
          // Set PI_MODEL_SERVER_SLOTS in the environment to match the
          // llama-server -np value. Default 1 is the safe reading: it makes the
          // block warn that a shared job blocks rather than merely slows.
          // Do not cite pi-config here: this bridge does not read it, and
          // test_taste_bridge asserts that any index.ts mentioning pi-config
          // also resolves the harness root from package.json.
          serverSlots: Number(process.env.PI_MODEL_SERVER_SLOTS ?? "1"),
        }),
      );
    },
  });

  pi.registerTool({
    name: "bg_status",
    label: "Background Status",
    description: "List background jobs and their state.",
    promptSnippet: "bg_status(): list background jobs dispatched with bg_start and their state.",
    parameters: Type.Object({}),
    async execute(_id, _params, _signal, _onUpdate, ctx: any) {
      return text(
        readJobs(ctx.cwd)
          .map((j) => `${j.id} · ${j.label} · ${j.state} · exit=${j.exitCode ?? "n/a"}`)
          .join("\n") || "[async-exec] no jobs",
      );
    },
  });

  pi.registerTool({
    name: "bg_cancel",
    label: "Background Cancel",
    description: "Cancel a running background job by id.",
    promptSnippet: "bg_cancel(id): stop a background job and its whole process tree.",
    parameters: Type.Object({
      id: Type.String({ description: "The job id returned by bg_start" }),
    }),
    async execute(_id, params: any, _signal, _onUpdate, ctx: any) {
      const job = readJobs(ctx.cwd).find((j) => j.id === params.id);
      if (!job || job.state !== "running") return text(`[async-exec] no running job ${params.id}`);
      if (job.pid !== null) killTree(job.pid);
      writeJob(ctx.cwd, { ...job, state: "cancelled", endedAt: Date.now(), acknowledged: true });
      release(ctx.cwd, job.id);
      return text(`[async-exec] cancelled ${params.id}`);
    },
  });

  pi.on("session_shutdown", async () => {
    dead = true;
    for (const t of timers) clearInterval(t);
    timers.clear();
  });

  // Reconcile only. This handler's result type is undefined — anything returned
  // from session_start is discarded, so the pending envelope cannot be delivered
  // from here. It goes out from before_agent_start below.
  pi.on("session_start", async (_event, ctx: any) => {
    const cwd: string = ctx.cwd;
    for (const j of reconcile(readJobs(cwd), isAlive)) writeJob(cwd, j);
  });

  // The only hook whose result carries a message (BeforeAgentStartEventResult).
  // A job that finished while nothing was listening — a crash, a killed session,
  // a wake that never landed — surfaces here on the next turn. Records are
  // marked acknowledged only once the message is actually being returned, so a
  // failure earlier in this handler leaves the notice on disk for next time.
  pi.on("before_agent_start", async (_event, ctx: any) => {
    if (dead) return;
    const cwd: string = ctx.cwd;
    const pending = readJobs(cwd).filter((j) => j.state !== "running" && !j.acknowledged);
    if (pending.length === 0) return;
    const content = buildEnvelope(pending, new Map());
    for (const j of pending) writeJob(cwd, { ...j, acknowledged: true });
    return { message: { customType: "async-exec", content, display: true } };
  });
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -v -k AsyncExecBridge`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add pi-extensions/async-exec-bridge/index.ts tests/test_async_exec_bridge.py
git commit -m "feat(async-exec): wire bg_start, bg_status and bg_cancel"
```

---

### Task 10: Notify the human when everything settles

**Files:**
- Modify: `pi-extensions/async-exec-bridge/index.ts`
- Test: `tests/test_async_exec_bridge.py`

**Interfaces:**
- Consumes: `jobs.ts` (`readJobs`).
- Produces: an `agent_settled` handler that notifies once, under two conditions.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_async_exec_bridge.py`:

```python
class TestAsyncExecBridgeNotification(unittest.TestCase):
    IDX = "pi-extensions/async-exec-bridge/index.ts"

    def test_notifies_on_agent_settled(self):
        """agent_settled is the only signal that Pi will not continue on its
        own. No other bridge in this repo uses it."""
        c = read(self.IDX)
        self.assertIn('pi.on("agent_settled"', c)

    def test_notification_is_best_effort(self):
        """A failed notification must never affect job state."""
        c = read(self.IDX)
        self.assertIn("ctx.ui?.notify?.(", c)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -v -k AsyncExecBridgeNotification`
Expected: FAIL — `agent_settled` not found.

- [ ] **Step 3: Write minimal implementation**

Add before the closing brace of `index.ts`:

```typescript
  pi.on("agent_settled", async (_event, ctx: any) => {
    const jobs = readJobs(ctx.cwd);
    // Only speak up if this session actually ran background work, and only
    // once nothing is still running — otherwise every ordinary conversation
    // would ping the user.
    const finished = jobs.filter((j) => j.state !== "running");
    if (finished.length === 0) return;
    if (jobs.some((j) => j.state === "running")) return;
    const failed = finished.filter((j) => j.state !== "done").length;
    ctx.ui?.notify?.(
      `[async-exec] ${finished.length} background job(s) finished, ${failed} not clean. Nothing left running.`,
      failed > 0 ? "warning" : "info",
    );
  });
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -v -k AsyncExecBridge`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add pi-extensions/async-exec-bridge/index.ts tests/test_async_exec_bridge.py
git commit -m "feat(async-exec): notify the user when everything settles"
```

---

### Task 11: End-to-end verification

**Files:**
- Create: `pi-extensions/async-exec-bridge/e2e-check.sh`

**Interfaces:**
- Consumes: the whole bridge.
- Produces: a script that proves dispatch → park → completion → resume works against a live Pi.

- [ ] **Step 1: Write the check script**

Create `pi-extensions/async-exec-bridge/e2e-check.sh`:

```bash
#!/usr/bin/env bash
# End-to-end proof that a background job wakes the agent.
#
# Requires a model server reachable at the configured apiBase. rpc mode exits
# the moment stdin hits EOF, so stdin is held open deliberately — an earlier
# spike read a dead process as "the timer never fired".
set -u
LOG="$(mktemp -d)/e2e.log"
export SPIKE_LOG="$LOG"

timeout 300 bash -c 'sleep 260 | pi --mode rpc --no-session \
  -e "pi-extensions/async-exec-bridge/index.ts" \
  "Use bg_start to run: sleep 20; echo DONE. Then PARK."' > "$LOG.rpc" 2>&1

turns=$(grep -oc '"type":"turn_end"' "$LOG.rpc" || echo 0)
woke=$(grep -c "async-exec" "$LOG.rpc" || echo 0)
echo "turn_end=$turns  async-exec messages=$woke"

# A check that only prints is a check that never fails.
if [ "$turns" -lt 2 ]; then
  echo "FAIL: expected at least 2 turn_end (dispatch turn + resumed turn), got $turns"
  exit 1
fi
if [ "$woke" -lt 1 ]; then
  echo "FAIL: no async-exec envelope reached the agent"
  exit 1
fi
echo "PASS"
```

- [ ] **Step 2: Run it**

Run: `bash pi-extensions/async-exec-bridge/e2e-check.sh`
Expected: `PASS` and exit code 0. The script fails loudly rather than printing numbers for a human to interpret.

- [ ] **Step 3: Record the wall-clock baseline**

Note dispatch-to-resume wall time in the commit message. Later changes that lengthen it mean something has been added to the wake path.

- [ ] **Step 4: Commit**

```bash
git add pi-extensions/async-exec-bridge/e2e-check.sh
git commit -m "test(async-exec): add end-to-end dispatch-to-resume check"
```

---

## Security surface, stated plainly

`bg_start` runs an arbitrary shell command **detached**, which is the point of
the feature and also its risk: the job outlives the agent being stopped, and it
is not covered by whatever guards apply to the ordinary `bash` tool. Interrupting
the agent does **not** interrupt its background work.

v1 mitigations, all already in the plan:

- `bg_cancel` is the explicit stop path, and it kills the whole process tree.
- `session_start` reconcile surfaces anything left running from a previous run,
  so nothing keeps going unnoticed.
- Every dispatch is recorded on disk with its command, so what was started is
  always auditable.

Not mitigated in v1: there is no allowlist and no confirmation prompt. If this
bridge is ever enabled for an untrusted prompt source, add one first.

## Known dead code in v1

`lease.ts` is fully implemented and tested, but v1 refuses `localModel:
"exclusive"`, so no lease is ever acquired and `beat()` /
`HEARTBEAT_INTERVAL_MS` are never called. This is deliberate — the module is
the finished half of a v2 feature whose other half is the GPU probe. Do not
delete it, and do not wire a heartbeat timer that has nothing to refresh.

## Deferred to v2 (do not build now)

- Cross-session daemon. State is already on disk; v2 adds a reader, not a rewrite.
- Job dependencies and DAG scheduling.
- Job priorities.
- Live GPU probing, and with it `localModel: "exclusive"`. Task 9 refuses `exclusive` outright because v1 cannot verify residency honestly; `preflight` already implements the real gate and its tests pass, so v2 only has to supply a probe and delete the early return. The duplicate, concurrency and lease gates are live today.
- Changing `planning-with-files-bridge`'s injection channel — separate concern, tracked in `docs/retro/2026-08-03-prefix-stabilization-has-a-price-tag.md`.
