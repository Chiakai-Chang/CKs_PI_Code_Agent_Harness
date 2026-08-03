import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { writeJob, readJobs, reconcile, deleteJob, type JobRecord } from "./jobs.ts";

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

test("deleteJob removes the record and its captured output together", () => {
  const cwd = mkdtempSync(join(tmpdir(), "aeb-"));
  writeJob(cwd, sample());
  const dir = `${cwd.replace(/\\/g, "/")}/.pi/async-exec`;
  writeFileSync(`${dir}/job-a3f1.out`, "output");
  writeFileSync(`${dir}/job-a3f1.out.rc`, "0");
  writeFileSync(`${dir}/job-a3f1.pid`, "1234");
  deleteJob(cwd, sample());
  assert.deepEqual(readdirSync(dir), []);
});

test("deleteJob on already-missing files is not an error", () => {
  const cwd = mkdtempSync(join(tmpdir(), "aeb-"));
  writeJob(cwd, sample());
  deleteJob(cwd, sample());
  deleteJob(cwd, sample());
  assert.deepEqual(readJobs(cwd), []);
});

const noCode = () => null;

test("reconcile marks running jobs with dead pids as orphaned", () => {
  const jobs = [sample({ id: "dead", pid: 999 }), sample({ id: "live", pid: 111 })];
  const changed = reconcile(jobs, (pid) => pid === 111, noCode);
  assert.equal(changed.length, 1);
  assert.equal(changed[0].id, "dead");
  assert.equal(changed[0].state, "orphaned");
});

test("reconcile leaves finished jobs alone", () => {
  const jobs = [sample({ id: "done", state: "done", pid: 999, exitCode: 0 })];
  assert.deepEqual(reconcile(jobs, () => false, noCode), []);
});

test("a job that finished while pi was being killed is reported by its exit code, not as orphaned", () => {
  // The pid is gone and no handler ever ran, but the shell wrapper had already
  // written the .rc file. Calling that "orphaned" throws away the one piece of
  // evidence the crash left behind — and reports a success as a failure.
  const changed = reconcile([sample({ id: "ok", pid: 999 })], () => false, () => 0);
  assert.equal(changed[0].state, "done");
  assert.equal(changed[0].exitCode, 0);
});

test("a job that had already failed when pi died keeps its real exit code", () => {
  const changed = reconcile([sample({ id: "bad", pid: 999 })], () => false, () => 3);
  assert.equal(changed[0].state, "failed");
  assert.equal(changed[0].exitCode, 3);
});

test("no exit code still means orphaned — absence is not success", () => {
  const changed = reconcile([sample({ id: "gone", pid: 999 })], () => false, () => null);
  assert.equal(changed[0].state, "orphaned");
  assert.equal(changed[0].exitCode, null);
});
