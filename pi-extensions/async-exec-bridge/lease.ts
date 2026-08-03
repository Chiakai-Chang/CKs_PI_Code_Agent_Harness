import { mkdirSync, readFileSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { leaseFile, runDir } from "./paths.ts";
import { LEASE_STALE_MS } from "./constants.ts";

export interface Lease {
  holderPid: number;
  jobId: string;
  beatAt: number;
}

/** Pure. A lease is dead if its holder is gone OR its heartbeat has aged out.
 *  Both checks matter: an orphaned process can hold a resource for hours while
 *  looking perfectly alive to a naive check. */
export function isStale(lease: Lease, now: number, isAlive: (pid: number) => boolean): boolean {
  if (!isAlive(lease.holderPid)) return true;
  return now - lease.beatAt > LEASE_STALE_MS;
}

export function readLease(cwd: string): Lease | null {
  try {
    return JSON.parse(readFileSync(leaseFile(cwd), "utf-8")) as Lease;
  } catch {
    return null;
  }
}

function put(cwd: string, lease: Lease): void {
  mkdirSync(runDir(cwd), { recursive: true });
  const target = leaseFile(cwd);
  const tmp = `${target}.tmp`;
  writeFileSync(tmp, JSON.stringify(lease), "utf-8");
  renameSync(tmp, target);
}

export function acquire(
  cwd: string,
  jobId: string,
  pid: number,
  now: number,
  isAlive: (pid: number) => boolean,
): boolean {
  const held = readLease(cwd);
  if (held && !isStale(held, now, isAlive)) return false;
  put(cwd, { holderPid: pid, jobId, beatAt: now });
  return true;
}

export function beat(cwd: string, now: number): void {
  const held = readLease(cwd);
  if (!held) return;
  put(cwd, { ...held, beatAt: now });
}

export function release(cwd: string, jobId: string): void {
  const held = readLease(cwd);
  if (!held || held.jobId !== jobId) return;
  try {
    rmSync(leaseFile(cwd));
  } catch {
    // Already gone.
  }
}
