import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { isAlive, killTree, readExitCode, readPid, startDetached } from "./spawn.ts";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

test("the job records a pid that is alive and killable, so a crashed parent can still recover it", async () => {
  // spawn() can return, and the parent can die, before the pid reaches the job
  // file — leaving a detached process that bg_cancel and reconcile cannot see.
  // The wrapper writes its own pid first thing, which closes that window.
  //
  // It is deliberately NOT asserted equal to the pid spawn() returned. On
  // Windows, Git's bin/bash.exe is a launcher: the pid Node gets back is the
  // wrapper (measured 23240) while the shell actually running the job is a
  // different process (11804). What the recovery path needs is a handle that is
  // alive and that killTree stops — which is what is asserted here.
  const dir = mkdtempSync(join(tmpdir(), "aeb-")).replace(/\\/g, "/");
  const out = `${dir}/out.txt`;
  const pidPath = `${dir}/out.pid`;
  const spawned = startDetached("sleep 30", dir, out, `${out}.rc`, pidPath) as number;
  await sleep(1500);
  const recorded = readPid(pidPath);
  assert.notEqual(recorded, null, "the job must record a pid");
  assert.equal(isAlive(recorded as number), true, "the recorded pid must be a live process");
  killTree(recorded as number);
  await sleep(1500);
  assert.equal(isAlive(recorded as number), false, "killTree on the recorded pid must stop it");
  killTree(spawned);
});

test("readPid on a missing file is null, not a guess", () => {
  assert.equal(readPid("/definitely/not/here.pid"), null);
});

test("a detached job keeps running after the caller returns", async () => {
  const dir = mkdtempSync(join(tmpdir(), "aeb-")).replace(/\\/g, "/");
  const out = `${dir}/out.txt`;
  const pid = startDetached("sleep 2; echo FINISHED", dir, out, `${out}.rc`, `${out}.pid`);
  assert.notEqual(pid, null);
  assert.equal(isAlive(pid as number), true);
  await sleep(3500);
  assert.match(readFileSync(out, "utf-8"), /FINISHED/);
});

test("a failing job reports its real exit code, not success", async () => {
  const dir = mkdtempSync(join(tmpdir(), "aeb-")).replace(/\\/g, "/");
  const out = `${dir}/out.txt`;
  startDetached("exit 3", dir, out, `${out}.rc`, `${out}.pid`);
  await sleep(2000);
  assert.equal(readExitCode(`${out}.rc`), 3);
});

test("an unfinished job has no exit code, and null must not read as success", async () => {
  const dir = mkdtempSync(join(tmpdir(), "aeb-")).replace(/\\/g, "/");
  const out = `${dir}/out.txt`;
  const pid = startDetached("sleep 30", dir, out, `${out}.rc`, `${out}.pid`) as number;
  assert.equal(readExitCode(`${out}.rc`), null);
  killTree(pid);
});

test("isAlive reports false for a pid that cannot exist", () => {
  assert.equal(isAlive(0x7ffffff0), false);
});

test("killTree stops a running job", async () => {
  const dir = mkdtempSync(join(tmpdir(), "aeb-")).replace(/\\/g, "/");
  const pid = startDetached("sleep 30", dir, `${dir}/out.txt`, `${dir}/out.txt.rc`, `${dir}/out.txt.pid`) as number;
  killTree(pid);
  await sleep(1500);
  assert.equal(isAlive(pid), false);
});
