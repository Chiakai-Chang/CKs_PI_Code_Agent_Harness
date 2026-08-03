import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { readTail } from "./capture.ts";

function tmpFile(content: string | Buffer): string {
  const p = join(mkdtempSync(join(tmpdir(), "aeb-")), "out.txt");
  writeFileSync(p, content);
  return p;
}

test("a short capture is returned whole", () => {
  assert.equal(readTail(tmpFile("hello"), 1024), "hello");
});

test("only the tail is returned, and only the tail is read", () => {
  // CAPTURE_MAX_BYTES is 8 MiB. Reading all of it into a string to keep 4 KiB
  // is a waste the envelope pays on every completion.
  const big = "x".repeat(5 * 1024 * 1024) + "THE-END";
  const out = readTail(tmpFile(big), 32);
  assert.ok(out.endsWith("THE-END"));
  assert.ok(Buffer.byteLength(out, "utf8") <= 32);
});

test("a missing file reads as empty, not as a throw", () => {
  assert.equal(readTail("/definitely/not/here.out", 128), "");
});

test("the tail still begins on a character boundary", () => {
  const out = readTail(tmpFile("中文輸出結尾"), 16);
  assert.ok(!out.includes("�"), `must not produce a replacement char: ${JSON.stringify(out)}`);
  assert.ok("中文輸出結尾".endsWith(out));
});
