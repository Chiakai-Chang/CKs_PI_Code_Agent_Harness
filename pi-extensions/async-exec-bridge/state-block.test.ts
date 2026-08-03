import { test } from "node:test";
import assert from "node:assert/strict";
import { stateBlock, type StateInput } from "./state-block.ts";
import type { JobRecord } from "./jobs.ts";

function job(over: Partial<JobRecord> = {}): JobRecord {
  return {
    id: "a3f1", label: "run integration suite", cmd: "npm test", cwd: "/tmp/p",
    localModel: "none", pid: 1, state: "running", startedAt: 0, endedAt: null,
    exitCode: null, outPath: "", acknowledged: false, ...over,
  };
}

function input(over: Partial<StateInput> = {}): StateInput {
  return {
    dispatched: job(), running: [job()], gpuCommittedGiB: 85.6, carveGiB: 96,
    contextTokens: 18_000, serverSlots: 1, ...over,
  };
}

test("the block states the job, the resources and the context depth", () => {
  const s = stateBlock(input());
  assert.match(s, /a3f1/);
  assert.match(s, /run integration suite/);
  assert.match(s, /localModel=none/);
  assert.match(s, /18K/);
});

test("it asks for a one-line PARK or CONTINUE decision", () => {
  const s = stateBlock(input());
  assert.match(s, /PARK/);
  assert.match(s, /CONTINUE/);
});

test("with a single server slot a shared job is described as blocking, not slowing", () => {
  const s = stateBlock(input({ dispatched: job({ localModel: "shared" }), serverSlots: 1 }));
  assert.match(s, /block/i);
  assert.doesNotMatch(s, /slows your own decode/i);
});

test("with no GPU probe the block says so rather than printing a made-up number", () => {
  const s = stateBlock({ ...input(), gpuCommittedGiB: undefined, carveGiB: undefined });
  assert.match(s, /not probed/);
  assert.doesNotMatch(s, /headroom/);
});

test("with several slots a shared job only slows the agent", () => {
  const s = stateBlock(input({ dispatched: job({ localModel: "shared" }), serverSlots: 4 }));
  assert.match(s, /slow/i);
});
