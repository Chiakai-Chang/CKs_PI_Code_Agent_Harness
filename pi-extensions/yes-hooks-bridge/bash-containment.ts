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

/**
 * Editors that rewrite their input files, but only when told to.
 *
 * `sed -i` was invisible here, and so to every guard that reads this function —
 * which is all three of the ones measured to change model behaviour. `perl` is
 * in the set because it is the same shape and the same test; covering one and
 * not the other leaves half a class open while looking closed.
 */
const IN_PLACE = new Set(["sed", "perl"]);
/** `-i`, `-i.bak`, `-pi`, `--in-place`. Not `-n`, `-E`, `-e`. */
const IN_PLACE_FLAG = /^(--in-place|-[a-zA-Z]*i)/;
/** Flags whose NEXT token is a script, not a file. */
const TAKES_ARG = new Set(["-e", "-f", "--expression", "--file"]);

/**
 * Files an in-place editor would rewrite, or [] when it only reads.
 *
 * The script is not a path. `sed -i -e 's|a|b|' f` naming `s|a|b|` as a target
 * would have containment refuse a legitimate edit because of this function's
 * own parsing — a guard blocking real work over its own mistake is how a guard
 * gets switched off, and a guard that is off protects nothing.
 */
function inPlaceTargets(tokens: string[]): string[] {
  if (!tokens.some((t) => IN_PLACE_FLAG.test(t))) return [];
  const files: string[] = [];
  let scriptSeen = false;
  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i];
    if (t.startsWith("-")) {
      if (TAKES_ARG.has(t)) {
        i++;            // the script rides with the flag
        scriptSeen = true;
      } else if (/^--(expression|file)=/.test(t)) {
        // No `t.includes("=")` guard in front: the pattern already requires one,
        // and the mutation sweep found the redundancy by surviving a flip of the
        // `&&` that nothing could observe. A condition no test can reach is a
        // condition to delete, not one to write a test for.
        scriptSeen = true;
      }
      continue;
    }
    if (!scriptSeen) {  // the bare first operand is the script
      scriptSeen = true;
      continue;
    }
    files.push(t);
  }
  return files;
}

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

/**
 * Operands with the redirections removed.
 *
 * Without this, `cp secret.txt D:/elsewhere/out.txt 2>/dev/null` reported its
 * destination as `2>/dev/null` — the last operand — and never looked at
 * `D:/elsewhere/out.txt`. The copy out of the project was allowed. Verified
 * 2026-08-10: the same command without the redirection is blocked, and with it
 * is not.
 *
 * `2>/dev/null` is ordinary shell hygiene, so this was reachable by accident and
 * not only on purpose. It surfaced while fixing the same omission in
 * `case-bridge/task-queue-guard.ts`, where the missing discard filter was
 * refusing innocent `ls … 2>/dev/null` calls — one omission, opposite failures,
 * two extractors.
 *
 * Handles both spellings: glued (`2>/dev/null`) and split (`> out.txt`), the
 * second of which must consume the token after it.
 */
function stripRedirections(tokens: string[]): string[] {
  const out: string[] = [];
  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i];
    if (/^\d?>>?$/.test(t) || /^\d?<$/.test(t)) {
      i++;                       // the target rides with the operator
      continue;
    }
    if (/^\d?>>?[^&]/.test(t) || /^\d?>>?&\d/.test(t)) continue;
    out.push(t);
  }
  return out;
}

export function isScratch(abs: string, raw?: string): boolean {
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
/**
 * Command segments, split on separators that are really separators.
 *
 * The separator positions come from the masked text so a `|` inside a quoted
 * script is not one, and the text comes from the original so quoted paths
 * survive. Splitting the raw command was fine until an in-place edit arrived
 * carrying `s|a|b|`.
 */
function segmentsOf(command: string, masked: string): string[] {
  const sep = /&&|\|\||;|\|/g;
  const parts: string[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = sep.exec(masked)) !== null) {
    parts.push(command.slice(last, m.index));
    last = m.index + m[0].length;
  }
  parts.push(command.slice(last));
  return parts;
}

/**
 * Interpreters that write files when handed inline code.
 *
 * Measured 2026-08-10, session 019fe880. The run wanted to write into the
 * harness install. In order: `write` refused, `write` refused, `write` refused,
 * `cat > …` refused, then `ECC_GATEGUARD=off bash -c 'printf … > …'` — an
 * attempt to switch a guard off — refused, and then:
 *
 *     python3 -c "import os; os.makedirs('D:/…/02_Task_Queue/Task_001_Inventory')"
 *     python3 << 'PYEOF' … open(base + '/role.md', 'w') …
 *     python3 << 'PYEOF' … output = r"""# Task_001_Inventory …"""
 *     python3 -c "with open(r'D:/…/status.txt','w') …"
 *
 * All four succeeded. A complete task package — role.md, recipe.md,
 * planning.md, a 5,188-byte output.md, status.txt — was written inside another
 * project. It went unnoticed for a day because that directory is gitignored and
 * the check used to declare the repository clean was `git status`, which cannot
 * see it.
 *
 * This is the fourth instance of one class: a guard that knows a fixed set of
 * write forms and meets a new one. `write`/`edit` only, then `tee -a`, then
 * `sed -i` and `dd of=`, now an interpreter.
 *
 * The file's own docstring says it closes common shapes rather than pretending
 * to sandbox bash, and that stands — but an interpreter is not an exotic shape.
 * It is what the model reached for immediately after two refusals, which makes
 * it the most common shape of all in the situation the guard exists for.
 */
const INTERPRETERS = new Set([
  "python", "python3", "py", "node", "nodejs", "perl", "ruby", "php", "deno", "bun",
  // A nested shell is an interpreter too, and the quoting hides everything
  // from the extractor above: in `bash -c 'printf x > D:/elsewhere/a'` the
  // redirection sits inside single quotes, so stripQuoted masks it and the
  // redirection scan sees nothing. The same run used it, behind an env-var
  // prefix, one call before it found python3.
  "bash", "sh", "zsh", "dash", "pwsh", "powershell",
]);
/** `-c`, `-e`, and the heredoc that carries a script on stdin. */
const INLINE_CODE = /(?:^|\s)-(?:c|e)(?:\s|$)|<<-?\s*['"]?\w+/;
/**
 * Absolute paths as they appear literally inside such a script.
 *
 * The path must START a token. Without that, the `\/` branch matched a slash in
 * the MIDDLE of one: `glob.glob('data/*.json')` yielded `/*.json`, which reads
 * as POSIX-absolute and therefore outside every project. Measured 2026-08-11 in
 * run 5 of T-A1 — two read-only `python3 -c` commands refused, and the model
 * spent ten calls writing a temp script to get the same answer.
 *
 * Group 1 is the path, so this needs `matchAll`, not `match`.
 */
const ABS_PATH = /(?:^|[\s'"`(=,;:[{])((?:[A-Za-z]:[\\/]|\/(?:[cdefgh]\/)?)[^\s'"`;|&)]+)/g;

/**
 * Escaping paths named inside an interpreter's inline code, or [].
 *
 * The guard cannot parse Python. It does not have to: the destination appeared
 * as a literal in the command every time, because a model writing a file spells
 * out where. Reading is left alone — a command is only refused when its literal
 * escapes the project AND an interpreter is being handed code, so
 * `python3 -c "print(open('/d/other/x').read())"` is the price of this rule and
 * is accepted: a read of another project is a much smaller problem than a write,
 * and a rule that tried to tell them apart would be parsing Python after all.
 */
function interpreterTargets(command: string, cwd: string): string[] {
  const masked = stripQuoted(command);
  const out: string[] = [];
  for (const seg of segmentsOf(command, masked)) {
    // `match` returns null or a non-empty array — never an empty one — so the
    // length half of this test was unreachable and the mutation sweep survived
    // removing it. Deleted rather than tested: a condition no input can reach is
    // a condition to delete.
    const tokens = seg.trim().match(/"[^"]*"|'[^']*'|[^\s]+/g);
    if (!tokens) continue;
    // Skip `VAR=value` prefixes. `ECC_GATEGUARD=off bash -c …` put the
    // assignment in tokens[0] and hid the command behind it — the same run
    // tried exactly that.
    let i = 0;
    while (i < tokens.length && /^[A-Za-z_][A-Za-z0-9_]*=/.test(tokens[i])) i++;
    const cmd = unquote(tokens[i] ?? "").split(/[\\/]/).pop() || "";
    if (!INTERPRETERS.has(cmd.replace(/\.exe$/i, ""))) continue;
    if (!INLINE_CODE.test(seg)) continue;
    for (const m of seg.matchAll(ABS_PATH)) {
      if (escapesCwd(m[1], cwd)) out.push(m[1]);
    }
  }
  return out;
}

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
  //
  // Segments are located in the MASKED text for the same reason redirection is:
  // `sed -i -e 's|a|b|' f` has a pipe inside its script, and splitting the raw
  // command tore that one command into four pieces.
  for (const seg of segmentsOf(command, masked)) {
    const tokens = seg.trim().match(/"[^"]*"|'[^']*'|[^\s]+/g);
    if (!tokens || tokens.length < 2) continue;
    // `VAR=value` prefixes hid the command: `ECC_GATEGUARD=off bash -c ...`
    // put the assignment in tokens[0], so `cp`/`mv`/`tee` behind one were
    // invisible too. Measured 2026-08-10 in session 019fe880.
    let first = 0;
    while (first < tokens.length && /^[A-Za-z_][A-Za-z0-9_]*=/.test(tokens[first])) first++;
    const cmd = unquote(tokens[first] ?? "").split("/").pop() || "";
    // Redirections were already collected above. Leaving them among the operands
    // let a trailing `2>/dev/null` stand in as a `cp`/`mv` destination and hide
    // the real one.
    const rest = stripRedirections(tokens.slice(first + 1).map(unquote));
    const args = rest.filter((t) => !t.startsWith("-"));
    if (cmd === "dd") {
      // `of=` is the output; `if=` is the input and must not be confused for it.
      for (const t of rest) if (t.startsWith("of=")) out.push(t.slice(3));
      continue;
    }
    if (IN_PLACE.has(cmd)) {
      out.push(...inPlaceTargets(rest));
      continue;
    }
    if (!args.length) continue;
    if (DEST_LAST.has(cmd)) out.push(args[args.length - 1]);
    else if (DEST_ALL.has(cmd)) out.push(...args);
  }

  // Discards dropped at extraction, not only at evaluation. `isScratch`
  // already ignored /dev/null downstream, so this changes no decision — it
  // keeps this extractor byte-identical to case-bridge's, which a test
  // asserts, and that parity is what stops the two drifting apart again.
  return out.filter(Boolean).filter((t) => !norm(t).startsWith("/dev/"));
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
/**
 * Commands that cannot write, so running them somewhere else is not a crossing.
 *
 * Deliberately an allowlist of READS. The set of things that write is unbounded
 * — six rounds of enumerating it is what produced this file — while the set of
 * things a run legitimately does in another directory is small and boring:
 * look at it. `cd /tmp && ls` and `cd ../other && git log` must keep working,
 * because this repo already has one guard permanently switched off for
 * misfiring, and that is the failure mode that costs the most.
 */
const READ_ONLY = new Set([
  "ls", "cat", "head", "tail", "less", "more", "wc", "stat", "file", "tree",
  "du", "df", "pwd", "echo", "printf", "which", "type", "basename", "dirname",
  "grep", "egrep", "fgrep", "rg", "ag", "find", "fd", "diff", "cmp", "md5sum",
  "sha256sum", "sort", "uniq", "cut", "awk", "sed", "date", "env", "true",
]);

/** `git` subcommands that only read. `git checkout` is not one of them. */
const GIT_READ_ONLY = new Set([
  "log", "status", "show", "diff", "branch", "remote", "config", "ls-files",
  "rev-parse", "describe", "blame", "shortlog", "cat-file", "tag",
]);

/** The first real word of a segment, skipping `VAR=value` prefixes. */
function headOf(segment: string): string[] {
  const tokens = segment.trim().match(/"[^"]*"|'[^']*'|[^\s]+/g) ?? [];
  let i = 0;
  while (i < tokens.length && /^[A-Za-z_][A-Za-z0-9_]*=/.test(tokens[i])) i++;
  return tokens.slice(i).map(unquote);
}

/**
 * Whether a DIRECTORY is scratch.
 *
 * `isScratch` answers for a path that names a file: its prefixes carry trailing
 * slashes, so `/tmp/run.log` is scratch and a bare `/tmp` is not. Asking about
 * the directory itself needs a child, and inventing one here reuses the audited
 * predicate instead of loosening it — a second, slightly different definition of
 * "scratch" is exactly the drift this repo keeps paying for.
 */
function isScratchDir(abs: string, raw: string): boolean {
  const child = (p: string) => `${p.replace(/[\\/]+$/, "")}/x`;
  return isScratch(child(abs), raw ? child(raw) : "");
}

/** The directory a `cd` segment moves to, or null when it is not a `cd`. */
function cdTargetOf(segment: string): string | null {
  const words = headOf(segment);
  if (words[0] !== "cd") return null;
  // `cd` with no argument goes home, and `cd -` goes back. Neither is a path
  // this guard can resolve, and guessing would be worse than saying nothing.
  const arg = words[1];
  if (!arg || arg === "-" || arg.startsWith("~")) return null;
  return arg;
}

/**
 * Whether a segment could write, given that it runs in someone else's project.
 *
 * `sed` and `awk` are in the read allowlist and can both write with the right
 * flags, so those two are checked for their in-place forms rather than trusted.
 */
function couldWrite(segment: string): boolean {
  const words = headOf(segment);
  if (!words.length) return false;
  const cmd = (words[0].split(/[\\/]/).pop() ?? "").replace(/\.exe$/i, "");
  if (cmd === "git") return !GIT_READ_ONLY.has(words[1] ?? "");
  if (cmd === "sed" || cmd === "perl") {
    return words.slice(1).some((w) => /^-[a-zA-Z]*i/.test(w) || w === "--in-place");
  }
  if (cmd === "awk") return segment.includes(">");
  if (!READ_ONLY.has(cmd)) return true;
  // A read command with a redirection is a write.
  return /(^|[^0-9<>&])>>?[^&]/.test(stripQuoted(segment));
}

/**
 * A `cd` out of the project, followed by something that could write.
 *
 * Measured 2026-08-12, run 10, call 23:
 *
 *     cd "<harness repo>" && node "external/mece-autopilot/scripts/…" --init "…"
 *
 * from a session whose workspace was elsewhere. It created `wiki/` and
 * `skills/` inside the harness repo, and every existing rule was blind to it:
 * there is no redirection, no copy destination, and no inline code — the path
 * that gets written is inside the script file, where this guard cannot look and
 * should not guess.
 *
 * So the `cd` is the tell, and it is also the more common form of the same hole:
 * after `cd D:/other-project`, `echo x > notes.md` is a relative path that the
 * old rule resolved against the SESSION's cwd and judged to be inside.
 *
 * Reads are unaffected by design — see READ_ONLY.
 */
function relocatedWrite(command: string, cwd: string): string | null {
  const masked = stripQuoted(command);
  let dir = cwd;
  // The raw token as written, kept beside the resolved path. `isScratch` needs
  // it: on Windows `resolve("/tmp")` becomes `D:/tmp`, and the leading slash —
  // the only thing that says "scratch" — is gone by then. Losing it turned
  // `cd /tmp && node build.js` into a refusal, which is the pre-registered
  // failure condition for this entire change.
  let raw = "";
  for (const seg of segmentsOf(command, masked)) {
    const target = cdTargetOf(seg);
    if (target !== null) {
      try {
        dir = isAbsolute(target) || /^[A-Za-z]:[\\/]/.test(target)
          ? resolve(target) : resolve(dir, target);
        raw = target;
      } catch {
        return null;                       // unparsable: this guard says nothing
      }
      continue;
    }
    if (!seg.trim()) continue;
    if (isScratchDir(dir, raw)) continue;
    if (!escapesCwd(dir, cwd)) continue;   // still inside the project
    if (couldWrite(seg)) return dir;
  }
  return null;
}

export function bashContainmentBlock(command: string, cwd: string): ContainmentBlock | null {
  if (typeof cwd !== "string" || !cwd) return null;
  let escaping: string[];
  try {
    escaping = writeTargets(command).filter((t) => escapesCwd(t, cwd));
    // An interpreter handed inline code writes wherever its literals point, and
    // this guard cannot parse the code. It does not need to — see
    // interpreterTargets, and session 019fe880, where four python3 calls wrote a
    // whole task package into another project after five refusals.
    escaping = escaping.concat(interpreterTargets(command, cwd));
  } catch {
    return null;
  }
  if (!escaping.length) {
    // Nothing visible escapes. The command may still have moved somewhere else
    // first — see relocatedWrite, and run 10 call 23, where `cd <other repo> &&
    // node <script>` left files in a project the session had never been in.
    let relocated: string | null = null;
    try {
      relocated = relocatedWrite(command, cwd);
    } catch {
      return null;
    }
    if (!relocated) return null;
    return {
      block: true,
      reason:
        `Directory containment (bash): this command runs in ${relocated}, ` +
        `outside the project root (${cwd}), and could write there. What it ` +
        `writes is inside the program it runs, where this guard cannot look — ` +
        `so the \`cd\` is what it goes on. A live run took exactly this route ` +
        `and created two directories in another repository. ` +
        `**Reading elsewhere is fine** (\`cd … && ls\`, \`git log\`, \`cat\`, ` +
        `\`grep\`): this refuses only a relocated command that could write. Run ` +
        `it from the project you were launched in, give it absolute paths inside ` +
        `that project, or ask the user first.`,
    };
  }
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
