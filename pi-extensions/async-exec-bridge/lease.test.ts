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
