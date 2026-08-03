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

export function leaseFile(cwd: string): string {
  return `${runDir(cwd)}/gpu.lease`;
}
