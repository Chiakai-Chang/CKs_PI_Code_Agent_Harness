/**
 * C.A.S.E. state transitions are tool calls, so they can be refused.
 *
 * Every transition in the protocol is one write to `status.txt`, and a write is
 * a `tool_call` — which fires *before* the tool runs, so the old value is still
 * on disk to compare against. That makes the state machine enforceable rather
 * than merely documented.
 *
 * It is worth saying why enforcement and not another reminder. Measured on this
 * harness in one day:
 *
 *   skill text ("cite each finding")        skipped 3/3
 *   systemPrompt note (task-shape routine)  delivered, 37 searches followed it
 *   core tier + full description            case-framework loaded 0/3
 *   tool_call {block, reason}               fired 3/3, URLs in files 0 -> 10/15
 *
 * The owner asked whether code could drive the framework's steps. It can, for
 * the half that is a transition. It cannot for the half that is a decision:
 * beginning to use C.A.S.E. has no before-state to compare with, which is
 * exactly why promoting the skill into the core tier changed nothing. These
 * guards say how the queue is worked; they say nothing about starting one.
 *
 * Scope is deliberately narrow — writes landing inside
 * `02_Task_Queue/Task_<NNN>_<slug>/`. A project that does not use C.A.S.E.
 * never meets any of this.
 *
 * The rules encoded here are the protocol's *invariants*, not its transition
 * table. Copying the table would fork it, and this repo already carries a scar
 * from a frozen fork. The authority remains
 * `external/Local-Agent-Workspace/references/for_agents.md`.
 */

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { missingDodArtifacts } from "./task-context.ts";
import { basename, dirname, join, resolve, sep } from "node:path";

export const VALID_STATUSES = ["PENDING", "IN_PROGRESS", "REVIEW", "DONE", "ESCALATED"];

/**
 * Transitions the protocol names. Anything not listed is *not* automatically
 * illegal — only the pairs in ILLEGAL below are refused.
 *
 * Being permissive here is deliberate. Every tightening in this harness has
 * produced a new evasion the moment it demanded more than it could check: the
 * citation gate took fabricated addresses from 0 to 4 in the run where it took
 * real ones from 0 to 10.
 */
export const LEGAL_TRANSITIONS: Record<string, string[]> = {
  PENDING: ["IN_PROGRESS", "ESCALATED"],
  IN_PROGRESS: ["REVIEW", "ESCALATED", "IN_PROGRESS"],
  REVIEW: ["DONE", "PENDING", "ESCALATED"],
  DONE: ["PENDING", "ESCALATED"],
  ESCALATED: ["PENDING", "IN_PROGRESS"],
};

/** Refused outright: a jump that skips the work or the review. */
const ILLEGAL = new Set(["PENDING>DONE", "PENDING>REVIEW", "IN_PROGRESS>DONE"]);

const TASK_DIR_RE = /^Task_(\d+)_/;
const QUEUE_DIR = "02_Task_Queue";
import { ApprovalRecord } from "./approval.ts";

const WRITE_TOOLS = new Set(["write", "edit"]);

/**
 * Paths a shell command would write to.
 *
 * A deliberate copy of `writeTargets` in yes-hooks-bridge/bash-containment.ts.
 * Installed bridges are sibling directories and a cross-bridge import is a
 * dependency waiting to break; two copies drift, so a parity test in
 * tests/test_case_guard_bash.py holds them to the same answers.
 *
 * Content is never extracted. `printf "DONE" >` would yield it, `cat > f << EOF`
 * and `echo $VAR >` would not, and partial parsing is worse than none: it would
 * imply the transition rules cover shell writes when they would only cover some
 * spellings of them.
 */
export function bashWriteTargets(command: unknown): string[] {
  if (typeof command !== "string" || !command.trim()) return [];
  const masked = command.replace(/"[^"]*"|'[^']*'/g, (m) => " ".repeat(m.length));
  const out: string[] = [];
  const unquote = (t: string) => t.replace(/^["']|["']$/g, "");

  const redir = /(^|[\s;&|])\d?>>?(?!&)/g;
  let m: RegExpExecArray | null;
  while ((m = redir.exec(masked)) !== null) {
    const token = command.slice(m.index + m[0].length).match(/^\s*("[^"]*"|'[^']*'|[^\s;&|<>]+)/);
    if (token) out.push(unquote(token[1]));
  }

  const DEST_LAST = new Set(["cp", "mv", "install", "rsync"]);
  const DEST_ALL = new Set(["mkdir", "touch", "tee"]);
  const IN_PLACE = new Set(["sed", "perl"]);
  const IN_PLACE_FLAG = /^(--in-place|-[a-zA-Z]*i)/;
  const TAKES_ARG = new Set(["-e", "-f", "--expression", "--file"]);

  // Separator positions come from the masked text: `sed -i -e 's|a|b|' f`
  // carries a pipe inside its script, and splitting the raw command tore that
  // one command into four pieces.
  const segments: string[] = [];
  const sep = /&&|\|\||;|\|/g;
  let last = 0;
  let sm: RegExpExecArray | null;
  while ((sm = sep.exec(masked)) !== null) {
    segments.push(command.slice(last, sm.index));
    last = sm.index + sm[0].length;
  }
  segments.push(command.slice(last));

  for (const seg of segments) {
    const tokens = seg.trim().match(/"[^"]*"|'[^']*'|[^\s]+/g);
    if (!tokens || tokens.length < 2) continue;
    const cmd = unquote(tokens[0]).split("/").pop() || "";
    // Redirections are already handled above; leaving them among the operands
    // made `cp a b 2>/dev/null` report its destination as "2>/dev/null" instead
    // of "b" — the guard then checked a path that does not exist and refused a
    // copy it had no opinion about. Found while fixing the discard filter, which
    // is the same omission one layer up.
    const rest = stripRedirections(tokens.slice(1).map(unquote));
    const args = rest.filter((t) => !t.startsWith("-"));
    if (cmd === "dd") {
      for (const t of rest) if (t.startsWith("of=")) out.push(t.slice(3));
      continue;
    }
    if (IN_PLACE.has(cmd)) {
      // Only with an in-place flag: `sed 's/a/b/' f` prints and writes nothing,
      // and a guard that refuses ordinary reads gets switched off.
      if (!rest.some((t) => IN_PLACE_FLAG.test(t))) continue;
      let scriptSeen = false;
      for (let i = 0; i < rest.length; i++) {
        const t = rest[i];
        if (t.startsWith("-")) {
          if (TAKES_ARG.has(t)) { i++; scriptSeen = true; }
          else if (/^--(expression|file)=/.test(t)) scriptSeen = true;
          continue;
        }
        if (!scriptSeen) { scriptSeen = true; continue; }
        out.push(t);
      }
      continue;
    }
    if (!args.length) continue;
    if (DEST_LAST.has(cmd)) out.push(args[args.length - 1]);
    else if (DEST_ALL.has(cmd)) out.push(...args);
  }
  return out.filter(Boolean).filter((t) => !isDiscard(t));
}

/**
 * A destination that discards, which is not a write anyone should guard.
 *
 * `2>/dev/null` was extracted as a write to `/dev/null`, and the phase gate has
 * no scratch filter, so it read every `ls … 2>/dev/null` as "writing a file that
 * is not status.txt" and refused it during CLAIM. Measured 2026-08-10 in session
 * 019fe880: of the model's first three calls, two carried `2>/dev/null` and both
 * were refused; the one without it was allowed. Nine of that run's sixteen
 * refusals came from this gate, while the single refusal that actually explained
 * the failure — a path resolved against the harness install — was drowned in
 * them.
 *
 * `bash-containment.ts` has had `isScratch` since it shipped. This extractor,
 * used by the phase gate, the queue guard and the claim detector, never got one.
 * The same omission in two places is why it took a live run to find: every unit
 * test fed it a real path.
 */
/**
 * Operands with the redirections removed.
 *
 * Handles both spellings: `2>/dev/null` glued into one token, and `> out.txt`
 * split across two. The second form has to consume the token after it, or the
 * filename becomes an operand of the command.
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

function isDiscard(target: string): boolean {
  const p = target.replace(/\\/g, "/").toLowerCase();
  return p === "/dev/null" || p === "nul" || p.startsWith("/dev/");
}

/** How many times one rule may refuse before it gives up for the session. */
export const MAX_BLOCKS_PER_RULE = 3;

export interface QueueBlock {
  block: true;
  reason: string;
}

type RuleName = "transition" | "one-at-a-time" | "self-approval" | "retro" | "boundary" | "tool-first";

/** The text a write or edit is about to put on disk. */
/**
 * The text a write would put on disk, or null when none can be read.
 *
 * null and "" have to be different answers. `bash` writes carry no parseable
 * content and this repo refuses to half-parse them (Task_004: partial parsing
 * is worse than none), so unreadable must keep passing — while an empty string
 * is a real value the model chose, and it broke a run.
 */
function outgoingText(input: unknown): string | null {
  const src = (input ?? {}) as Record<string, unknown>;
  const parts: string[] = [];
  let found = false;
  if (typeof src.content === "string") { parts.push(src.content); found = true; }
  const edits = src.edits;
  if (Array.isArray(edits)) {
    for (const e of edits) {
      const t = (e as Record<string, unknown> | null)?.newText;
      if (typeof t === "string") { parts.push(t); found = true; }
    }
  }
  return found ? parts.join("\n") : null;
}

/**
 * The `Task_<NNN>_<slug>` directory a path sits in, or null.
 *
 * Walks up rather than pattern-matching the whole path so a file nested deeper
 * (`inputs/data.csv`) still resolves to its task package.
 */
export function taskDirOf(target: string): string | null {
  let dir = dirname(resolve(target));
  let seen = 0;
  while (seen++ < 32) {
    const name = basename(dir);
    const parent = dirname(dir);
    if (TASK_DIR_RE.test(name) && basename(parent) === QUEUE_DIR) return dir;
    if (parent === dir) return null;
    dir = parent;
  }
  return null;
}

function readStatus(taskDir: string): string | null {
  try {
    const raw = readFileSync(join(taskDir, "status.txt"), "utf8").trim();
    return VALID_STATUSES.includes(raw) ? raw : null;
  } catch {
    return null;
  }
}

/** Task directories currently at IN_PROGRESS, by name. */
function openTasks(queueDir: string): string[] {
  try {
    return readdirSync(queueDir)
      .filter((n) => TASK_DIR_RE.test(n))
      .filter((n) => readStatus(join(queueDir, n)) === "IN_PROGRESS");
  } catch {
    return [];
  }
}

export class TaskQueueGuard {
  /**
   * The user's approval, seen by the bridge rather than reported by the model.
   *
   * Fed from `before_agent_start`, whose `prompt` is documented as "the raw
   * user prompt text (after expansion)". Nothing the model writes reaches it:
   * `blocked-claim` measured a run announcing "已執行完畢" for a call that had
   * just been refused.
   */
  readonly humanApproved = new ApprovalRecord();

  /** Task directories this session moved to IN_PROGRESS — the Worker's own. */
  private startedHere = new Set<string>();
  private blocked = new Map<RuleName, number>();
  private retired = new Set<RuleName>();

  /**
   * Returns a refusal, or null.
   *
   * Fails open on everything it cannot read: a missing or unreadable
   * `status.txt` means there is no old value to compare, and refusing on a
   * guess is worse than allowing.
   */
  check(toolName: string, input: unknown, _cwd?: string): QueueBlock | null {
    try {
      return this.evaluate(toolName, input);
    } catch {
      return null;
    }
  }

  private evaluate(toolName: string, input: unknown): QueueBlock | null {
    const name = String(toolName || "").toLowerCase();
    if (name === "bash") return this.checkBash(input);
    if (!WRITE_TOOLS.has(name)) return null;

    const src = (input ?? {}) as Record<string, unknown>;
    const target = typeof src.path === "string" ? src.path : "";
    if (!target) return null;

    const taskDir = taskDirOf(target);
    if (!taskDir) return null;
    const queueDir = dirname(taskDir);
    const taskName = basename(taskDir);

    if (basename(resolve(target)) === "status.txt") {
      return this.checkTransition(taskDir, queueDir, taskName, outgoingText(input));
    }
    return this.checkBoundary(queueDir, taskName);
  }

  private checkTransition(
    taskDir: string, queueDir: string, taskName: string, written: string | null,
  ): QueueBlock | null {
    // Unreadable content keeps passing: `bash` writes carry none, and this repo
    // refuses to half-parse them.
    if (written === null) return null;
    const next = written.trim();

    // REVERSAL, recorded rather than quietly deleted. This line used to read
    //     if (!VALID_STATUSES.includes(next)) return null;  // the verifier's business
    // so the guard checked transitions BETWEEN valid states and never checked
    // that the value was a state at all.
    //
    // Measured 2026-08-09: a run claimed its task, then wrote COMPLETE, then an
    // empty string, and both were allowed. One invalid write stops the machine —
    // every later nextStep() reads a status it cannot parse, falls back to
    // "claim this task", and repeats it while the model believes it has
    // finished. That run never reached REVIEW.
    //
    // The deferral was deliberate and there is no verifier in this loop. The
    // scar on record is that undocumented rejections get rebuilt; this is the
    // other half, where a documented one outlives its reason.
    //
    // The contract is tighter than "one of five": refuse exactly what
    // `readStatus` would later fail to read, which is why lowercase is refused
    // too — it would stop the machine the same way by a politer route.
    if (!VALID_STATUSES.includes(next) && this.refuse("status-value")) {
      return {
        block: true,
        reason:
          `C.A.S.E. status guard: ${taskName}/status.txt would be set to ` +
          `"${next.slice(0, 40)}", which is not a status. The state machine ` +
          `reads this file every turn, so an unrecognised value stops it — the ` +
          `advancer falls back to "claim this task" and repeats that while you ` +
          `carry on. Exactly one of these, upper case: ` +
          `${VALID_STATUSES.join(", ")}.`,
      };
    }
    if (!VALID_STATUSES.includes(next)) return null;
    const current = readStatus(taskDir);
    if (!current) return null;                         // nothing to compare

    if (ILLEGAL.has(`${current}>${next}`) && this.refuse("transition")) {
      const allowed = (LEGAL_TRANSITIONS[current] || []).join(", ");
      return {
        block: true,
        reason:
          `C.A.S.E. transition guard: ${taskName} is ${current} and this sets it ` +
          `to ${next}, which skips the work or the review. From ${current} the ` +
          `protocol allows: ${allowed}. Take the next step instead of the last one.`,
      };
    }

    if (next === "IN_PROGRESS" && current !== "IN_PROGRESS") {
      const open = openTasks(queueDir).filter((n) => n !== taskName);
      if (open.length > 0 && this.refuse("one-at-a-time")) {
        return {
          block: true,
          reason:
            `C.A.S.E. one-at-a-time guard: ${open.join(", ")} is already ` +
            `IN_PROGRESS. A queue worked two tasks at once is a queue in name ` +
            `only — the reason to have one is that each piece gets finished ` +
            `before the next begins. Close it (REVIEW) or escalate it first.`,
        };
      }
    }

    if (next === "REVIEW" && current !== "REVIEW") {
      // The composition gap: every other rule here passed and the task still
      // arrived at REVIEW empty. See task-context.ts::missingDodArtifacts —
      // REVIEW is what summons a human under Path A, so an empty one asks
      // someone to accept an empty folder.
      let missing: string[] = [];
      try {
        missing = missingDodArtifacts(taskDir, _cwd, existsSync);
      } catch {
        missing = [];                      // unparsable recipe: not this guard's call
      }
      if (missing.length && this.refuse("dod-artifacts")) {
        return {
          block: true,
          reason:
            `C.A.S.E. 驗收物守衛:${taskName} 要進 REVIEW,但 recipe.md 的 Local DoD ` +
            `點名的檔案還不存在:${missing.join("、")}。` +
            `REVIEW 是叫人來驗收的狀態 —— 現在讓人來,他會看到一個空資料夾。` +
            `先把那些檔案寫出來,再改狀態。` +
            `(如果那一條 DoD 其實不需要產出檔案,就改 recipe.md 把它寫清楚。)`,
        };
      }
    }

    if (next === "DONE") {
      if (!existsSync(join(taskDir, "retro.md")) && this.refuse("retro")) {
        return {
          block: true,
          reason:
            `C.A.S.E. retrospective guard: ${taskName} has no retro.md, and ` +
            `Section 13a makes one mandatory before every DONE. Write what went ` +
            `wrong, what could be better, what was learned, and what C.A.S.E. ` +
            `itself should change — then close the task.`,
        };
      }
      // Session boundary as the proxy for "a fresh context". Path B of the
      // protocol (autonomous Checker approval, for unattended runs) allows the
      // same model to approve — but explicitly "in a fresh context", and §1
      // makes role separation non-negotiable. So this costs an unattended run a
      // session boundary per task, which is the protocol's price rather than
      // this guard's, and pi-skills/commands/case.md says so up front.
      // Path A first: the protocol's DEFAULT for supervised deployments is a
      // human approving in the chat, and there the Checker IS the person, so
      // Section 1 is satisfied without a second session. This guard used to
      // refuse regardless, which made Path A unexecutable and pushed the
      // review work back onto the user — "a Worker must not self-approve" read
      // as "must change session". The evidence is a real user prompt seen by
      // the bridge at before_agent_start, never anything the model says.
      if (this.startedHere.has(taskDir) && this.humanApproved.take()) return null;
      if (this.startedHere.has(taskDir) && this.refuse("self-approval")) {
        return {
          block: true,
          reason:
            `C.A.S.E. dual-track guard: this session moved ${taskName} to ` +
            `IN_PROGRESS, so it is the Worker and cannot also be the Checker. ` +
            `Section 1 is satisfied either way — but somebody other than the ` +
            `Worker has to say so. Two ways: report the result to the user and ` +
            `let them approve in the chat (Path A, the protocol's default for ` +
            `supervised runs), or leave it at REVIEW for a fresh session to ` +
            `check output.md against recipe.md's Local DoD (Path B). What is ` +
            `not allowed is closing it on your own word.`,
        };
      }
    }

    if (next === "IN_PROGRESS") this.startedHere.add(taskDir);
    return null;
  }

  /**
   * Shell writes into a task package.
   *
   * Measured 2026-08-06: a task went PENDING to DONE with none of the five
   * rules firing, because every status change was `printf ... > status.txt`.
   * Section 1's dual-track rule — non-negotiable — was among the bypassed.
   *
   * `status.txt` is refused outright rather than inspected, and the reason
   * cites the protocol's own Tool-First Rule, whose example of what never to do
   * is word for word what was observed. Any other file in a task package falls
   * through to the boundary rule, which needs no content either.
   */
  private checkBash(input: unknown): QueueBlock | null {
    const command = (input as { command?: unknown } | undefined)?.command;
    for (const target of bashWriteTargets(command)) {
      const taskDir = taskDirOf(target);
      if (!taskDir) continue;
      const queueDir = dirname(taskDir);
      const taskName = basename(taskDir);
      if (basename(resolve(target)) === "status.txt") {
        if (!this.refuse("tool-first")) return null;
        return {
          block: true,
          reason:
            `C.A.S.E. tool-first guard: this changes ${taskName}'s status with a ` +
            `shell redirect, which the protocol names as the thing never to do ` +
            `(SKILL.md §4: "NEVER run host shell redirection commands, e.g. ` +
            `echo \"IN_PROGRESS\" > status.txt"). It also steps around every ` +
            `state rule, because those watch the write tool — a run reached DONE ` +
            `this way with no dual-track check at all. Use \`write\` on ` +
            `${taskName}/status.txt instead.`,
        };
      }
      const refusal = this.checkBoundary(queueDir, taskName);
      if (refusal) return refusal;
    }
    return null;
  }

  /**
   * Section 5's permission boundary: a Worker writes inside its own task
   * folder. With nothing open, nothing is the wrong task.
   */
  private checkBoundary(queueDir: string, taskName: string): QueueBlock | null {
    const open = openTasks(queueDir);
    if (open.length !== 1) return null;
    if (open[0] === taskName) return null;
    if (!this.refuse("boundary")) return null;
    return {
      block: true,
      reason:
        `C.A.S.E. boundary guard: ${open[0]} is the task in progress, and this ` +
        `writes into ${taskName}. A task package is self-contained; work that ` +
        `belongs to another task belongs in that task's turn.`,
    };
  }

  /**
   * Records a refusal and reports whether it should be delivered.
   *
   * A rule declined three times will not work on the fourth, and further
   * refusals can only deadlock the session. Same reasoning, and same budget, as
   * the gates in yes-hooks-bridge.
   */
  private refuse(rule: RuleName): boolean {
    if (this.retired.has(rule)) return false;
    const count = (this.blocked.get(rule) ?? 0) + 1;
    this.blocked.set(rule, count);
    if (count > MAX_BLOCKS_PER_RULE) {
      this.retired.add(rule);
      return false;
    }
    return true;
  }

  /** A new session is a new Worker. */
  reset(): void {
    this.startedHere.clear();
    this.blocked.clear();
    this.retired.clear();
  }
}
