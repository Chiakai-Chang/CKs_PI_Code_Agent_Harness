/**
 * The bash-shaped hole in the directory-containment guard.
 *
 * Measured 2026-08-06 in a live run. Pi was launched in a temp directory and
 * asked to set a task's status. In order:
 *
 *     write  D:/MyProject/CKs_PI_Code_Agent_Harness/02_Task_Queue/.../status.txt
 *            -> BLOCKED by containmentGuard
 *     bash   echo "DONE" > "D:/MyProject/.../02_Task_Queue/.../status.txt"
 *            -> allowed
 *     ...four bash calls hunting for the directory...
 *     bash   mkdir -p ".../external/Local-Agent-Workspace/.../Task_001_Probe/"
 *              && echo "DONE" > ".../status.txt"
 *            -> allowed; wrote into this harness's own vendored submodule
 *     then reported success to the user
 *
 * `containmentGuard` was wired to `write` and `edit` only. Refused there, the
 * run reached for `bash` and got through — into the very submodule the
 * vendored-skill guard exists to protect, and past the guard that was added
 * because a run once "wrote files into a sibling project AND edited this
 * harness's own scripts".
 *
 * This closes the common shapes rather than pretending to sandbox bash. A shell
 * can do anything, and a guard that claims otherwise is worse than one with a
 * stated limit: it catches redirection, `tee`, `cp`/`mv` destinations and
 * `mkdir`, and fails open on everything it cannot parse.
 *
 * Scratch locations stay allowed on purpose. Writing to /tmp, %TEMP% or
 * /dev/null is ordinary work; a guard that refuses it gets switched off within
 * a day, and then it protects nothing at all.
 */

import { isAbsolute, resolve, sep } from "node:path";

/** Commands whose destination argument is a write target. */
const DEST_LAST = new Set(["cp", "mv", "install", "rsync"]);
const DEST_ALL = new Set(["mkdir", "touch", "tee"]);

/** Written to constantly and owned by nobody's project. */
const SCRATCH_PREFIXES = [
  "/tmp/", "/var/tmp/", "/dev/",
];

const SCRATCH_ENV = ["TEMP", "TMP", "TMPDIR"];

export interface ContainmentBlock {
  block: true;
  reason: string;
}

function norm(p: string): string {
  return p.replace(/\\/g, "/").replace(/\/+$/, "").toLowerCase();
}

/** Quoted spans hide operators: `echo "a > b"` redirects nothing. */
function stripQuoted(command: string): string {
  return command.replace(/"[^"]*"|'[^']*'/g, (m) => " ".repeat(m.length));
}

/** The same spans, but keeping their contents — used to recover real paths. */
function unquote(token: string): string {
  return token.replace(/^["']|["']$/g, "");
}

function isScratch(abs: string, raw?: string): boolean {
  const p = norm(abs);
  // The raw token matters as much as the resolved path: on Windows,
  // resolve("/tmp/x") becomes "D:/tmp/x" because a leading slash is
  // drive-relative, and `> /dev/null` would then read as another project.
  const r = norm(raw ?? "");
  if (SCRATCH_PREFIXES.some((s) => p.startsWith(s) || r.startsWith(s))) return true;
  for (const key of SCRATCH_ENV) {
    const v = process.env[key];
    if (v && p.startsWith(norm(v) + "/")) return true;
  }
  // Windows temp roots, which env vars do not always spell the same way.
  return /^[a-z]:\/(users\/[^/]+\/appdata\/local\/temp|windows\/temp|temp)\//.test(p);
}

/**
 * Paths a command would write to.
 *
 * Operates on the quote-stripped command so operators inside strings are not
 * mistaken for real ones, then reads the corresponding token out of the
 * original text so the path itself survives its quotes.
 */
export function writeTargets(command: string): string[] {
  if (typeof command !== "string" || !command.trim()) return [];
  const masked = stripQuoted(command);
  const out: string[] = [];

  // Redirection: `> path`, `>> path`. `2>&1` and `>&2` are descriptors.
  //
  // The operator is located in the masked text so one inside a string is not
  // mistaken for a real one, and the target is then read from the ORIGINAL at
  // that offset. Reading it from the masked text instead was the first version,
  // and it missed `echo "DONE" > "D:/..."` — a quoted path had been blanked
  // out, which is precisely the command the live run used.
  // The operator only. Letting the pattern also consume the following
  // whitespace was the second version's bug: masking turns a quoted path into
  // spaces of the same length, so `\s*` swallowed the whole target and left the
  // offset at the end of the line. Whitespace and token are both read from the
  // original.
  const redir = /(^|[\s;&|])\d?>>?(?!&)/g;
  let m: RegExpExecArray | null;
  while ((m = redir.exec(masked)) !== null) {
    const rest = command.slice(m.index + m[0].length);
    const token = rest.match(/^\s*("[^"]*"|'[^']*'|[^\s;&|<>]+)/);
    if (token) out.push(unquote(token[1]));
  }

  // Command destinations. Tokens are read from the original so quoted paths
  // containing spaces are still recovered as one argument.
  const segments = command.split(/(?:&&|\|\||;|\|)/);
  for (const seg of segments) {
    const tokens = seg.trim().match(/"[^"]*"|'[^']*'|[^\s]+/g);
    if (!tokens || tokens.length < 2) continue;
    const cmd = unquote(tokens[0]).split("/").pop() || "";
    const args = tokens.slice(1).map(unquote).filter((t) => !t.startsWith("-"));
    if (!args.length) continue;
    if (DEST_LAST.has(cmd)) out.push(args[args.length - 1]);
    else if (DEST_ALL.has(cmd)) out.push(...args);
  }

  return out.filter(Boolean);
}

/** Whether a target lands outside the project and is not scratch. */
export function escapesCwd(target: string, cwd: string): boolean {
  if (!target || !cwd) return false;
  let abs: string;
  try {
    abs = isAbsolute(target) || /^[A-Za-z]:[\\/]/.test(target)
      ? resolve(target)
      : resolve(cwd, target);
  } catch {
    return false;
  }
  if (isScratch(abs, target)) return false;
  const root = norm(resolve(cwd));
  const p = norm(abs);
  return p !== root && !p.startsWith(root + "/");
}

/**
 * Refuses a bash command that would write outside the project.
 *
 * Fails open on an unreadable command or an unknown cwd — a shell command it
 * cannot parse is a command it has no business refusing.
 */
export function bashContainmentBlock(command: string, cwd: string): ContainmentBlock | null {
  if (typeof cwd !== "string" || !cwd) return null;
  let escaping: string[];
  try {
    escaping = writeTargets(command).filter((t) => escapesCwd(t, cwd));
  } catch {
    return null;
  }
  if (!escaping.length) return null;
  return {
    block: true,
    reason:
      `Directory containment (bash): this command writes to ${escaping[0]}, ` +
      `outside the project root (${cwd}). The write tool already refuses this ` +
      `and a shell redirect is the same act — a live run took exactly that ` +
      `route and left a file inside another repository's vendored submodule. ` +
      `Write inside the project you were launched in, use a temp directory for ` +
      `scratch, or ask the user if you genuinely need to touch somewhere else.`,
  };
}
