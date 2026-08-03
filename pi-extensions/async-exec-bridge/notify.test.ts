import { test } from "node:test";
import assert from "node:assert/strict";
import { settleNotification } from "./notify.ts";
import type { JobRecord } from "./jobs.ts";

function job(over: Partial<JobRecord> = {}): JobRecord {
  return {
    id: "a", label: "a", cmd: "x", cwd: "/tmp/p", localModel: "none", pid: 1,
    state: "done", startedAt: 0, endedAt: 1000, exitCode: 0, outPath: "",
    acknowledged: true, ...over,
  };
}

test("an ordinary conversation with no background work says nothing", () => {
  assert.equal(settleNotification([job()], new Set(), new Set()), null);
});

test("it reports the jobs this session saw finish", () => {
  const r = settleNotification([job({ id: "a" })], new Set(["a"]), new Set());
  assert.deepEqual(r, { ids: ["a"], finished: 1, failed: 0 });
});

test("jobs from a previous run are not counted", () => {
  // Job records outlive the session that wrote them.
  const r = settleNotification(
    [job({ id: "old" }), job({ id: "mine" })],
    new Set(["mine"]),
    new Set(),
  );
  assert.deepEqual(r, { ids: ["mine"], finished: 1, failed: 0 });
});

test("nothing is said while a job is still running", () => {
  const r = settleNotification(
    [job({ id: "a" }), job({ id: "b", state: "running" })],
    new Set(["a"]),
    new Set(),
  );
  assert.equal(r, null);
});

test("a failed job is counted as not clean", () => {
  const r = settleNotification(
    [job({ id: "a", state: "failed", exitCode: 1 })],
    new Set(["a"]),
    new Set(),
  );
  assert.deepEqual(r, { ids: ["a"], finished: 1, failed: 1 });
});

test("the same result is never announced twice", () => {
  // agent_settled fires at the end of EVERY turn. Without this, one background
  // job means a notification after every single reply for the rest of the
  // session — the ordinary conversation the spec says not to interrupt.
  assert.equal(settleNotification([job({ id: "a" })], new Set(["a"]), new Set(["a"])), null);
});

test("a later job still gets announced after an earlier one was", () => {
  const r = settleNotification(
    [job({ id: "first" }), job({ id: "second" })],
    new Set(["first", "second"]),
    new Set(["first"]),
  );
  assert.deepEqual(r, { ids: ["second"], finished: 1, failed: 0 });
});
