import type { JobRecord } from "./jobs.ts";

export interface SettleNotification {
  /** Job ids covered by this notification. The caller records them so the same
   *  result is never announced a second time. */
  ids: string[];
  finished: number;
  failed: number;
}

/** Pure. Decides whether `agent_settled` should say anything, and about what.
 *
 *  Three conditions, each learned the hard way:
 *
 *  - Only jobs THIS session saw finish count. Job records outlive the session
 *    that wrote them, so counting the run directory made a single dispatch
 *    report "2 background job(s) finished" — one of them from a previous run.
 *  - Nothing is said while a job is still running: settling with work
 *    outstanding is not "done".
 *  - Nothing is said twice. `agent_settled` fires at the end of EVERY turn, so
 *    without `alreadyNotified` one background job means a ping after every
 *    single reply for the rest of the session. That is the ordinary
 *    conversation the design set out not to interrupt. */
export function settleNotification(
  jobs: JobRecord[],
  finishedThisSession: ReadonlySet<string>,
  alreadyNotified: ReadonlySet<string>,
): SettleNotification | null {
  if (finishedThisSession.size === 0) return null;
  if (jobs.some((j) => j.state === "running")) return null;
  const fresh = jobs.filter((j) => finishedThisSession.has(j.id) && !alreadyNotified.has(j.id));
  if (fresh.length === 0) return null;
  return {
    ids: fresh.map((j) => j.id),
    finished: fresh.length,
    failed: fresh.filter((j) => j.state !== "done").length,
  };
}
