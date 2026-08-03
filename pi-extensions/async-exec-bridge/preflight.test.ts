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
