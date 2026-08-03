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
