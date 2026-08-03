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

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -v -k AsyncExecBridge`
Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git add pi-extensions/async-exec-bridge pi-extensions/bridge-manifest.json scripts/restore.py tests/test_async_exec_bridge.py
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
  - `interface PreflightInput { jobs: JobRecord[]; cmd: string; cwd: string; localModel: LocalModel; leaseHeld: boolean; gpuCommittedGiB: number; cleanBaselineGiB: number; }`
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
   *  counts shared system memory and would wave a doomed job through. */
  gpuCommittedGiB: number;
  cleanBaselineGiB: number;
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
Expected: PASS, 8 tests.

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
  gpuCommittedGiB: number;
  carveGiB: number;
  contextTokens: number;
  /** llama-server slot count. At 1, a "shared" job serialises at the server:
   *  the agent's own decode stops rather than merely slowing. */
  serverSlots: number;
}

export function stateBlock(i: StateInput): string {
  const d = i.dispatched;
  const headroom = (i.carveGiB - i.gpuCommittedGiB).toFixed(1);
  const depthK = `${Math.round(i.contextTokens / 1000)}K`;

  const lines = [
    `[bg] dispatched job ${d.id} · "${d.label}" · localModel=${d.localModel}`,
    `[bg] running: ${i.running.length}    GPU committed: ${i.gpuCommittedGiB.toFixed(1)} GiB / ${i.carveGiB} GiB carve (headroom ${headroom} GiB)`,
    `[bg] your context depth: ~${depthK} — prefill and decode both get slower as this grows`,
  ];

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
Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git add pi-extensions/async-exec-bridge/state-block.ts pi-extensions/async-exec-bridge/state-block.test.ts
git commit -m "feat(async-exec): add deliberation state block"
```

---

### Task 8: Verify detached spawn survives on Windows

This is the one platform assumption the spec deliberately left unverified. Do it before wiring `bg_start`, because a failure here changes the design.

**Files:**
- Create: `pi-extensions/async-exec-bridge/spawn.ts`
- Test: `pi-extensions/async-exec-bridge/spawn.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `startDetached(cmd: string, cwd: string, outPath: string): number | null` — returns the pid, or null if spawn failed
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
import { isAlive, killTree, startDetached } from "./spawn.ts";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

test("a detached job keeps running after the caller returns", async () => {
  const dir = mkdtempSync(join(tmpdir(), "aeb-")).replace(/\\/g, "/");
  const out = `${dir}/out.txt`;
  const pid = startDetached("sleep 2; echo FINISHED", dir, out);
  assert.notEqual(pid, null);
  assert.equal(isAlive(pid as number), true);
  await sleep(3500);
  assert.match(readFileSync(out, "utf-8"), /FINISHED/);
});

test("isAlive reports false for a pid that cannot exist", () => {
  assert.equal(isAlive(0x7ffffff0), false);
});

test("killTree stops a running job", async () => {
  const dir = mkdtempSync(join(tmpdir(), "aeb-")).replace(/\\/g, "/");
  const pid = startDetached("sleep 30", dir, `${dir}/out.txt`) as number;
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
import { openSync } from "node:fs";

const SHELL = process.env.SHELL_PATH || "C:/Program Files/Git/bin/bash.exe";

/** Start a job that outlives the caller. stdout and stderr both go to a file so
 *  nothing depends on this process staying around to drain a pipe. */
export function startDetached(cmd: string, cwd: string, outPath: string): number | null {
  const fd = openSync(outPath, "a");
  const child = spawn(SHELL, ["-lc", cmd], {
    cwd,
    detached: true,
    stdio: ["ignore", fd, fd],
    windowsHide: true,
  });
  if (child.pid === undefined) return null;
  child.unref();
  return child.pid;
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
Expected: PASS, 3 tests.

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
- Test: `tests/test_async_exec_bridge.py`

**Interfaces:**
- Consumes: every module from Tasks 2-8.
- Produces: tools `bg_start`, `bg_status`, `bg_cancel` registered on the Pi extension API.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_async_exec_bridge.py`:

```python
class TestAsyncExecBridgeTools(unittest.TestCase):
    IDX = "pi-extensions/async-exec-bridge/index.ts"

    def test_registers_the_three_tools(self):
        c = read(self.IDX)
        for tool in ("bg_start", "bg_status", "bg_cancel"):
            self.assertIn(f'pi.registerTool("{tool}"', c)

    def test_dispatch_runs_preflight_before_spawning(self):
        c = read(self.IDX)
        self.assertLess(c.index("preflight("), c.index("startDetached("))

    def test_result_is_written_before_the_wake_attempt(self):
        """Waking can fail and be retried; state cannot."""
        c = read(self.IDX)
        self.assertLess(c.index("writeJob("), c.index("pi.sendMessage("))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -v -k AsyncExecBridgeTools`
Expected: FAIL — `bg_start` not found in `index.ts`.

- [ ] **Step 3: Write minimal implementation**

Replace the body of `pi-extensions/async-exec-bridge/index.ts`:

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { randomBytes } from "node:crypto";
import { readFileSync } from "node:fs";
import { JOB_TIMEOUT_MS } from "./constants.ts";
import { buildEnvelope, tailBytes } from "./envelope.ts";
import { readJobs, reconcile, writeJob, type JobRecord, type LocalModel } from "./jobs.ts";
import { outFile } from "./paths.ts";
import { preflight } from "./preflight.ts";
import { readLease, release } from "./lease.ts";
import { isAlive, killTree, startDetached } from "./spawn.ts";
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

  pi.registerTool("bg_start", {
    description:
      "Start a long-running command in the background and return immediately. " +
      "You will be woken with the result when it finishes.",
    handler: async (args: { cmd: string; label?: string; localModel?: LocalModel }, ctx: any) => {
      const cwd: string = ctx.cwd;
      const localModel: LocalModel = args.localModel ?? "none";
      // v1 has no live GPU probe, so the residency check cannot be honest.
      // Refuse outright rather than pretend to have checked — a wrong "yes"
      // here means two large models racing for memory.
      if (localModel === "exclusive") {
        return (
          '[async-exec] refused: localModel "exclusive" is not supported yet — ' +
          "v1 has no live GPU residency probe, so it cannot verify a second model would fit. " +
          'Use "shared" to reuse the running server, or use a cloud model.'
        );
      }
      const jobs = readJobs(cwd);
      const gate = preflight({
        jobs,
        cmd: args.cmd,
        cwd,
        localModel,
        leaseHeld: readLease(cwd) !== null,
        gpuCommittedGiB: CLEAN_BASELINE_GIB,
        cleanBaselineGiB: CLEAN_BASELINE_GIB,
      });
      if (gate.ok === false) return `[async-exec] refused: ${gate.reason}`;
      if (gate.ok === "duplicate") return `[async-exec] already running as job ${gate.id}`;

      const id = randomBytes(2).toString("hex");
      const out = outFile(cwd, id);
      const pid = startDetached(args.cmd, cwd, out);
      if (pid === null) return "[async-exec] refused: could not start the process";


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
        finish(cwd, ctx, job, "done", 0);
      }, 2000);
      timers.add(poll);

      return stateBlock({
        dispatched: job,
        running: readJobs(cwd).filter((j) => j.state === "running"),
        gpuCommittedGiB: CLEAN_BASELINE_GIB,
        carveGiB: 96,
        contextTokens: 0,
        serverSlots: 1,
      });
    },
  });

  pi.registerTool("bg_status", {
    description: "List background jobs and their state.",
    handler: async (_args: unknown, ctx: any) =>
      readJobs(ctx.cwd)
        .map((j) => `${j.id} · ${j.label} · ${j.state} · exit=${j.exitCode ?? "n/a"}`)
        .join("\n") || "[async-exec] no jobs",
  });

  pi.registerTool("bg_cancel", {
    description: "Cancel a running background job by id.",
    handler: async (args: { id: string }, ctx: any) => {
      const job = readJobs(ctx.cwd).find((j) => j.id === args.id);
      if (!job || job.state !== "running") return `[async-exec] no running job ${args.id}`;
      if (job.pid !== null) killTree(job.pid);
      writeJob(ctx.cwd, { ...job, state: "cancelled", endedAt: Date.now(), acknowledged: true });
      release(ctx.cwd, job.id);
      return `[async-exec] cancelled ${args.id}`;
    },
  });

  pi.on("session_shutdown", async () => {
    dead = true;
    for (const t of timers) clearInterval(t);
    timers.clear();
  });

  pi.on("session_start", async (_event, ctx: any) => {
    const cwd: string = ctx.cwd;
    for (const j of reconcile(readJobs(cwd), isAlive)) writeJob(cwd, j);
    const pending = readJobs(cwd).filter((j) => j.state !== "running" && !j.acknowledged);
    if (pending.length === 0) return;
    for (const j of pending) writeJob(cwd, { ...j, acknowledged: true });
    return { message: { customType: "async-exec", content: buildEnvelope(pending, new Map()), display: true } };
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

echo "--- events ---"
grep -oE '"type":"(agent_start|turn_start|turn_end|agent_end|agent_settled)"' "$LOG.rpc" | sort | uniq -c
echo "--- did the agent wake after the job finished? ---"
grep -c "async-exec" "$LOG.rpc"
```

- [ ] **Step 2: Run it**

Run: `bash pi-extensions/async-exec-bridge/e2e-check.sh`
Expected: at least two `turn_end` events — one for the dispatch turn, one for the resumed turn — and at least one `async-exec` message.

- [ ] **Step 3: Record the wall-clock baseline**

Note dispatch-to-resume wall time in the commit message. Later changes that lengthen it mean something has been added to the wake path.

- [ ] **Step 4: Commit**

```bash
git add pi-extensions/async-exec-bridge/e2e-check.sh
git commit -m "test(async-exec): add end-to-end dispatch-to-resume check"
```

---

## Deferred to v2 (do not build now)

- Cross-session daemon. State is already on disk; v2 adds a reader, not a rewrite.
- Job dependencies and DAG scheduling.
- Job priorities.
- Live GPU probing, and with it `localModel: "exclusive"`. Task 9 refuses `exclusive` outright because v1 cannot verify residency honestly; `preflight` already implements the real gate and its tests pass, so v2 only has to supply a probe and delete the early return. The duplicate, concurrency and lease gates are live today.
- Changing `planning-with-files-bridge`'s injection channel — separate concern, tracked in `docs/retro/2026-08-03-prefix-stabilization-has-a-price-tag.md`.
