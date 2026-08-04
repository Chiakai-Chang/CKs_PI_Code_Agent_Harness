import { JOB_TIMEOUT_MS, MAX_JOB_TIMEOUT_MS, MIN_JOB_TIMEOUT_MS } from "./constants.ts";

/** Pure. Turns a requested per-job timeout into one that will actually work.
 *
 *  The value comes from the model, so it is clamped rather than trusted. The
 *  NaN guard is not decoration: every comparison against NaN is false, so an
 *  unguarded NaN passes both bound checks and then makes
 *  `Date.now() - startedAt > timeout` false forever — a job that can never time
 *  out, which is the one outcome this whole mechanism exists to prevent. */
export function resolveTimeout(requested: number | undefined): number {
  if (requested === undefined) return JOB_TIMEOUT_MS;
  if (!Number.isFinite(requested)) return JOB_TIMEOUT_MS;
  if (requested <= 0) return JOB_TIMEOUT_MS;
  return Math.round(Math.min(MAX_JOB_TIMEOUT_MS, Math.max(MIN_JOB_TIMEOUT_MS, requested)));
}
