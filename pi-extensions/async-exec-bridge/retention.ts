import type { JobRecord } from "./jobs.ts";

/** Pure. Picks the job records safe to delete.
 *
 *  Deliberately conservative — the run directory is the only durable record
 *  that a background job ever existed, and it is what crash recovery reads.
 *  Two things are therefore never pruned regardless of age:
 *
 *    - a `running` job, because pruning it orphans a live process; and
 *    - an unacknowledged result, because that is a completion nobody has been
 *      told about yet. Deleting it is exactly the data loss the whole
 *      write-to-disk-first design exists to prevent.
 *
 *  Everything else is kept for `retentionMs`, and beyond `maxKept` records the
 *  oldest go first. A finished record with no `endedAt` is aged by `startedAt`,
 *  so a malformed record cannot accumulate forever. */
export function selectPrunable(
  jobs: JobRecord[],
  now: number,
  retentionMs: number,
  maxKept: number,
): JobRecord[] {
  const eligible = jobs.filter((j) => j.state !== "running" && j.acknowledged);
  const age = (j: JobRecord) => now - (j.endedAt ?? j.startedAt);

  const expired = eligible.filter((j) => age(j) > retentionMs);
  const remaining = eligible
    .filter((j) => age(j) <= retentionMs)
    .sort((a, b) => age(a) - age(b));

  const overCap = remaining.slice(maxKept);
  return [...expired, ...overCap];
}
