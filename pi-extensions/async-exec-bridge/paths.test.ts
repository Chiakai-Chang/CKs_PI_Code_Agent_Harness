import { test } from "node:test";
import assert from "node:assert/strict";
import { runDir, jobFile, outFile, pidFile, leaseFile } from "./paths.ts";

test("all artefacts live under the project run directory", () => {
  const cwd = "/tmp/proj";
  assert.equal(runDir(cwd), "/tmp/proj/.pi/async-exec");
  assert.equal(jobFile(cwd, "a3f1"), "/tmp/proj/.pi/async-exec/job-a3f1.json");
  assert.equal(outFile(cwd, "a3f1"), "/tmp/proj/.pi/async-exec/job-a3f1.out");
  assert.equal(pidFile(cwd, "a3f1"), "/tmp/proj/.pi/async-exec/job-a3f1.pid");
  assert.equal(leaseFile(cwd), "/tmp/proj/.pi/async-exec/gpu.lease");
});

test("paths are normalised to forward slashes", () => {
  assert.equal(runDir("C:\\proj"), "C:/proj/.pi/async-exec");
});
