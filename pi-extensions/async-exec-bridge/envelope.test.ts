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
