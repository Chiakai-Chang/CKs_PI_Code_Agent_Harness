function norm(p: string): string {
  return p.replace(/\\/g, "/").replace(/\/+$/, "");
}

export function runDir(cwd: string): string {
  return `${norm(cwd)}/.pi/async-exec`;
}

export function jobFile(cwd: string, id: string): string {
  return `${runDir(cwd)}/job-${id}.json`;
}

export function outFile(cwd: string, id: string): string {
  return `${runDir(cwd)}/job-${id}.out`;
}

/** The job's own record of its pid, written by the shell wrapper itself.
 *  Needed because the parent can die between spawn() returning and the pid
 *  reaching disk — leaving a detached process nothing can find. */
export function pidFile(cwd: string, id: string): string {
  return `${runDir(cwd)}/job-${id}.pid`;
}

export function leaseFile(cwd: string): string {
  return `${runDir(cwd)}/gpu.lease`;
}
