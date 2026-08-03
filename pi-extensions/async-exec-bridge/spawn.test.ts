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
