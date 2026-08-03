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

test("tailBytes counts bytes, not JS string units", () => {
  // Every CJK character is 3 bytes in UTF-8. Slicing by string length let a
  // constant named ENVELOPE_TAIL_BYTES inject roughly three times its budget
  // whenever the output was not ASCII.
  const s = "工作輸出".repeat(50); // 200 chars, 600 bytes
  const out = tailBytes(s, 60);
  assert.ok(Buffer.byteLength(out, "utf8") <= 60, "must respect the byte budget");
  assert.ok(out.length > 0);
});

test("tailBytes never cuts a multi-byte character in half", () => {
  const s = "中文輸出結尾";
  // 16 bytes is deliberately not a multiple of 3, so a naive byte slice lands
  // mid-character and decodes to U+FFFD.
  const out = tailBytes(s, 16);
  assert.ok(!out.includes("�"), `must not produce a replacement char: ${JSON.stringify(out)}`);
  assert.ok(s.endsWith(out), "must still be a suffix of the input");
});

test("tailBytes never splits a surrogate pair", () => {
  const s = `padding${"🔥".repeat(10)}`;
  const out = tailBytes(s, 9); // an emoji is 4 bytes; 9 is not a multiple of 4
  assert.ok(!out.includes("�"), "must not produce a replacement char");
  assert.ok(s.endsWith(out), "must still be a suffix of the input");
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
