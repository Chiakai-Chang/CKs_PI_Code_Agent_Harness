import { spawn, spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { CAPTURE_MAX_BYTES } from "./constants.ts";

/** Same resolution order as stealth-web-bridge's findShell(). spawn("bash")
 *  relies on the *process* PATH, which on Windows often does not include Git's
 *  bash — that is the "spawn sh ENOENT" that stopped that bridge from ever
 *  cold-starting. Ask the harness first, then known locations, then PATH.
 *  A machine-specific path must never be the only answer. */
function findShell(): string {
  if (process.env.PI_HARNESS_SHELL) return process.env.PI_HARNESS_SHELL;
  try {
    const cfg = JSON.parse(readFileSync(join(homedir(), ".pi", "agent", "settings.json"), "utf-8"));
    if (cfg.shellPath && existsSync(cfg.shellPath)) return cfg.shellPath;
  } catch {
    // No harness settings; fall through.
  }
  for (const c of [
    "C:\\Program Files\\Git\\bin\\bash.exe",
    "C:\\Program Files\\Git\\usr\\bin\\bash.exe",
    "C:\\Program Files (x86)\\Git\\bin\\bash.exe",
  ]) {
    try {
      if (existsSync(c)) return c;
    } catch {
      // Unreadable candidate; try the next.
    }
  }
  return "bash";
}

const SHELL = findShell();

/** Start a job that outlives the caller. stdout and stderr both go to a file so
 *  nothing depends on this process staying around to drain a pipe. */
export function startDetached(
  cmd: string,
  cwd: string,
  outPath: string,
  rcPath: string,
  pidPath: string,
): number | null {
  // Everything goes through shell-level redirection, and stdio stays "ignore".
  // VERIFIED on Windows: a detached child does NOT reliably receive an
  // inherited file descriptor - stdio: ["ignore", fd, fd] produced an empty
  // output file every time, while the shell redirect below captures both
  // streams. This also matches Node's documented recommendation of pairing
  // detached with stdio: "ignore".
  //
  // head -c caps the capture so a runaway job cannot fill the disk.
  // PIPESTATUS[0] is the command's status, not head's. Caveat: once head has
  // taken its bytes it closes the pipe, so a job that keeps writing past
  // CAPTURE_MAX_BYTES dies of SIGPIPE and PIPESTATUS[0] reads 141 rather than
  // its own code. That is a real misreport, but only for jobs exceeding 8 MiB
  // of output, and 141 is at least not silently 0.
  //
  // Record the pid first: the parent can die between spawn() returning and the
  // pid reaching the job file, and a detached process nothing has a pid for
  // cannot be cancelled or reconciled — it just holds resources until the
  // machine is rebooted. Having the job record its own pid closes that window
  // from the inside.
  //
  // `$$` alone is WRONG on Windows. Under Git Bash (MSYS) it is the MSYS pid,
  // a different namespace from the Windows pid that spawn() returns and that
  // taskkill and process.kill understand — measured 1388 vs 17924 for the same
  // process. MSYS exposes the mapping at /proc/<pid>/winpid; on a real POSIX
  // box that path does not exist and `$$` is already correct.
  const recordPid =
    `{ if [ -r /proc/$$/winpid ] ; then cat /proc/$$/winpid ; else echo $$ ; fi ; } ` +
    `> ${JSON.stringify(pidPath)}`;
  const wrapped =
    `${recordPid} ; ` +
    `{ ${cmd} ; } 2>&1 | head -c ${CAPTURE_MAX_BYTES} > ${JSON.stringify(outPath)} ; ` +
    `echo \${PIPESTATUS[0]} > ${JSON.stringify(rcPath)}`;
  const child = spawn(SHELL, ["-lc", wrapped], {
    cwd,
    detached: true,
    stdio: "ignore",
    windowsHide: true,
  });
  if (child.pid === undefined) return null;
  child.unref();
  return child.pid;
}

/** Exit code recorded by the shell wrapper, or null if the job never got that
 *  far (killed, machine lost power). null must NOT be treated as success. */
export function readExitCode(rcPath: string): number | null {
  try {
    const n = Number.parseInt(readFileSync(rcPath, "utf-8").trim(), 10);
    return Number.isNaN(n) ? null : n;
  } catch {
    return null;
  }
}

/** The pid the job recorded for itself, or null if it never got that far.
 *  Used to recover a job whose pid never reached its job record. */
export function readPid(pidPath: string): number | null {
  try {
    const n = Number.parseInt(readFileSync(pidPath, "utf-8").trim(), 10);
    return Number.isNaN(n) ? null : n;
  } catch {
    return null;
  }
}

export function isAlive(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

/** On Windows, killing a pid does NOT kill its children. An orphan left behind
 *  can hold a resource for hours and make the next run look like an unsupported
 *  configuration rather than a busy machine. */
export function killTree(pid: number): void {
  if (process.platform === "win32") {
    spawnSync("taskkill", ["/PID", String(pid), "/T", "/F"], { windowsHide: true });
    return;
  }
  try {
    process.kill(-pid, "SIGKILL");
  } catch {
    try {
      process.kill(pid, "SIGKILL");
    } catch {
      // Already gone.
    }
  }
}
