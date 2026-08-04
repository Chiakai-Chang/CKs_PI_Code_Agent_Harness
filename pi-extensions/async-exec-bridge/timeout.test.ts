import { test } from "node:test";
import assert from "node:assert/strict";
import { resolveTimeout } from "./timeout.ts";
import { JOB_TIMEOUT_MS, MAX_JOB_TIMEOUT_MS, MIN_JOB_TIMEOUT_MS } from "./constants.ts";

test("no override means the default", () => {
  assert.equal(resolveTimeout(undefined), JOB_TIMEOUT_MS);
});

test("a sensible override is honoured", () => {
  assert.equal(resolveTimeout(5 * 60 * 1000), 5 * 60 * 1000);
});

test("an override below the floor is raised, not obeyed", () => {
  // A one-second timeout kills the job before most commands have started, and
  // the model has no way to know that.
  assert.equal(resolveTimeout(1), MIN_JOB_TIMEOUT_MS);
});

test("an override above the ceiling is capped", () => {
  assert.equal(resolveTimeout(365 * 24 * 60 * 60 * 1000), MAX_JOB_TIMEOUT_MS);
});

test("nonsense falls back to the default rather than disabling the timeout", () => {
  // Number.NaN comparisons are all false, so an unguarded NaN would sail
  // through every bound check and then never trigger the timeout at all.
  for (const bad of [Number.NaN, Number.POSITIVE_INFINITY, -1, 0]) {
    const got = resolveTimeout(bad);
    assert.ok(
      got >= MIN_JOB_TIMEOUT_MS && got <= MAX_JOB_TIMEOUT_MS,
      `${bad} produced ${got}, outside the permitted range`,
    );
  }
});

test("a fractional override is not left fractional", () => {
  assert.equal(Number.isInteger(resolveTimeout(90_000.7)), true);
});
