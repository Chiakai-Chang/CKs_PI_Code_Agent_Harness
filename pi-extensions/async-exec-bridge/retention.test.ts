import { test } from "node:test";
import assert from "node:assert/strict";
import { selectPrunable } from "./retention.ts";
import type { JobRecord } from "./jobs.ts";

const DAY = 24 * 60 * 60 * 1000;
const NOW = 100 * DAY;

function job(over: Partial<JobRecord> = {}): JobRecord {
  return {
    id: "a", label: "a", cmd: "x", cwd: "/tmp/p", localModel: "none", pid: 1,
    state: "done", startedAt: NOW - DAY, endedAt: NOW - DAY, exitCode: 0,
    outPath: "", acknowledged: true, ...over,
  };
}

test("a fresh finished job is kept", () => {
  assert.deepEqual(selectPrunable([job()], NOW, 7 * DAY, 50), []);
});

test("a finished job past the retention window is pruned", () => {
  const old = job({ id: "old", endedAt: NOW - 8 * DAY });
  assert.deepEqual(selectPrunable([old], NOW, 7 * DAY, 50).map((j) => j.id), ["old"]);
});

test("a running job is never pruned, however old", () => {
  const ancient = job({ id: "r", state: "running", endedAt: null, startedAt: NOW - 90 * DAY });
  assert.deepEqual(selectPrunable([ancient], NOW, 7 * DAY, 50), []);
});

test("an unacknowledged result is never pruned — it has not been reported yet", () => {
  // This is the crash-recovery notice. Deleting it loses the only record that
  // the job ever ran, which is the opposite of what retention is for.
  const unread = job({ id: "u", acknowledged: false, endedAt: NOW - 90 * DAY });
  assert.deepEqual(selectPrunable([unread], NOW, 7 * DAY, 50), []);
});

test("beyond the count cap the oldest are pruned first", () => {
  const jobs = [
    job({ id: "newest", endedAt: NOW - 1 * DAY }),
    job({ id: "middle", endedAt: NOW - 2 * DAY }),
    job({ id: "oldest", endedAt: NOW - 3 * DAY }),
  ];
  assert.deepEqual(selectPrunable(jobs, NOW, 7 * DAY, 2).map((j) => j.id), ["oldest"]);
});

test("the count cap still refuses to touch running or unreported jobs", () => {
  const jobs = [
    job({ id: "keep1", endedAt: NOW - 1 * DAY }),
    job({ id: "run", state: "running", endedAt: null, startedAt: NOW - 50 * DAY }),
    job({ id: "unread", acknowledged: false, endedAt: NOW - 50 * DAY }),
  ];
  assert.deepEqual(selectPrunable(jobs, NOW, 7 * DAY, 1), []);
});

test("a finished job with no endedAt falls back to startedAt rather than living forever", () => {
  const odd = job({ id: "odd", endedAt: null, startedAt: NOW - 30 * DAY });
  assert.deepEqual(selectPrunable([odd], NOW, 7 * DAY, 50).map((j) => j.id), ["odd"]);
});
