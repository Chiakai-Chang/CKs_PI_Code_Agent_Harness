import { MAX_CONCURRENT_JOBS } from "./constants.ts";
import type { JobRecord, LocalModel } from "./jobs.ts";

export interface PreflightInput {
  jobs: JobRecord[];
  cmd: string;
  cwd: string;
  localModel: LocalModel;
  leaseHeld: boolean;
  /** Committed adapter memory, not reported free memory: the reported figure
   *  counts shared system memory and would wave a doomed job through.
   *  Optional because v1 has no probe — undefined means "not measured", which
   *  the exclusive gate treats as a refusal, not as an idle GPU. */
  gpuCommittedGiB?: number;
  cleanBaselineGiB?: number;
}

export type PreflightResult =
  | { ok: true }
  | { ok: false; reason: string }
  | { ok: "duplicate"; id: string };

export function preflight(i: PreflightInput): PreflightResult {
  const dup = i.jobs.find((j) => j.state === "running" && j.cmd === i.cmd && j.cwd === i.cwd);
  if (dup) return { ok: "duplicate", id: dup.id };

  const running = i.jobs.filter((j) => j.state === "running").length;
  if (running >= MAX_CONCURRENT_JOBS) {
    return { ok: false, reason: `at the concurrent job limit (${MAX_CONCURRENT_JOBS}); park until one finishes` };
  }

  if (i.localModel === "exclusive") {
    if (i.leaseHeld) {
      return { ok: false, reason: "the GPU lease is held by another job" };
    }
    if (i.gpuCommittedGiB === undefined || i.cleanBaselineGiB === undefined) {
      return {
        ok: false,
        reason:
          "GPU residency is not probed, so it cannot be verified that a second local model would fit. " +
          'Use localModel "shared" to reuse the running server, or use a cloud model.',
      };
    }
    if (i.gpuCommittedGiB > i.cleanBaselineGiB) {
      return {
        ok: false,
        reason:
          `a local model is resident (${i.gpuCommittedGiB.toFixed(1)} GiB committed vs ` +
          `${i.cleanBaselineGiB.toFixed(1)} GiB idle baseline); a second one will not fit. ` +
          `Use localModel "shared" to reuse the running server, use a cloud model, ` +
          `or stop the main server first.`,
      };
    }
  }

  return { ok: true };
}
