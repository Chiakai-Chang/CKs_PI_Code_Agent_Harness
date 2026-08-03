import { mkdirSync, readdirSync, readFileSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { jobFile, outFile, pidFile, runDir } from "./paths.ts";

export type JobState = "running" | "done" | "failed" | "timeout" | "cancelled" | "orphaned";
export type LocalModel = "none" | "shared" | "exclusive";

export interface JobRecord {
  id: string;
  label: string;
  cmd: string;
  cwd: string;
  localModel: LocalModel;
  pid: number | null;
  state: JobState;
  startedAt: number;
  endedAt: number | null;
  exitCode: number | null;
  outPath: string;
  /** True once its envelope has been delivered to the agent. Survives crashes
   *  so a completed-but-unreported job is not silently lost. */
  acknowledged: boolean;
}

/** Write via temp + rename so a crash mid-write cannot leave a partial record. */
export function writeJob(cwd: string, job: JobRecord): void {
  const dir = runDir(cwd);
  mkdirSync(dir, { recursive: true });
  const target = jobFile(cwd, job.id);
  const tmp = `${target}.tmp`;
  writeFileSync(tmp, JSON.stringify(job, null, 2), "utf-8");
  renameSync(tmp, target);
}

export function readJobs(cwd: string): JobRecord[] {
  const dir = runDir(cwd);
  let names: string[];
  try {
    names = readdirSync(dir);
  } catch {
    return [];
  }
  const out: JobRecord[] = [];
  for (const n of names) {
    if (!n.startsWith("job-") || !n.endsWith(".json")) continue;
    try {
      out.push(JSON.parse(readFileSync(`${dir}/${n}`, "utf-8")) as JobRecord);
    } catch {
      // A partial or corrupt record is skipped rather than crashing startup.
    }
  }
  return out;
}

/** Delete a job's record and everything captured alongside it. Best effort:
 *  a file already gone is the desired end state, not an error. */
export function deleteJob(cwd: string, job: JobRecord): void {
  for (const p of [
    jobFile(cwd, job.id),
    outFile(cwd, job.id),
    `${outFile(cwd, job.id)}.rc`,
    pidFile(cwd, job.id),
  ]) {
    try {
      rmSync(p);
    } catch {
      // Already gone.
    }
  }
}

/** Pure. Returns only the records whose state changed.
 *
 *  `readCode` supplies the exit code the shell wrapper recorded, or null when
 *  the job never got that far. It matters because a job can finish in the
 *  instant pi is being killed: no handler runs, but the .rc file is already on
 *  disk. Marking that "orphaned" would discard the only evidence the crash left
 *  behind, and would report a clean success as a failure. A null code still
 *  means orphaned — absence of a code is not success. */
export function reconcile(
  jobs: JobRecord[],
  isAlive: (pid: number) => boolean,
  readCode: (job: JobRecord) => number | null,
): JobRecord[] {
  const changed: JobRecord[] = [];
  for (const j of jobs) {
    if (j.state !== "running") continue;
    if (j.pid !== null && isAlive(j.pid)) continue;
    const code = readCode(j);
    changed.push(
      code === null
        ? { ...j, state: "orphaned", endedAt: Date.now() }
        : { ...j, state: code === 0 ? "done" : "failed", exitCode: code, endedAt: Date.now() },
    );
  }
  return changed;
}
