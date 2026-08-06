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
  for (const seg of command.split(/(?:&&|\|\||;|\|)/)) {
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

/** How many times one rule may refuse before it gives up for the session. */
export const MAX_BLOCKS_PER_RULE = 3;

export interface QueueBlock {
  block: true;
  reason: string;
}

type RuleName = "transition" | "one-at-a-time" | "self-approval" | "retro" | "boundary" | "tool-first";

/** The text a write or edit is about to put on disk. */
function outgoingText(input: unknown): string {
  const src = (input ?? {}) as Record<string, unknown>;
  const parts: string[] = [];
  if (typeof src.content === "string") parts.push(src.content);
  const edits = src.edits;
  if (Array.isArray(edits)) {
    for (const e of edits) {
      const t = (e as Record<string, unknown> | null)?.newText;
      if (typeof t === "string") parts.push(t);
    }
  }
  return parts.join("\n");
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
      return this.checkTransition(taskDir, queueDir, taskName, outgoingText(input).trim());
    }
    return this.checkBoundary(queueDir, taskName);
  }

  private checkTransition(
    taskDir: string, queueDir: string, taskName: string, next: string,
  ): QueueBlock | null {
    if (!VALID_STATUSES.includes(next)) return null;   // the verifier's business
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
      if (this.startedHere.has(taskDir) && this.refuse("self-approval")) {
        return {
          block: true,
          reason:
            `C.A.S.E. dual-track guard: this session moved ${taskName} to ` +
            `IN_PROGRESS, so it is the Worker and cannot also be the Checker. ` +
            `Section 1 makes that non-negotiable, and Path B's autonomous ` +
            `approval still requires a FRESH context. Leave it at REVIEW, start ` +
            `a new session, and check output.md against recipe.md's Local DoD ` +
            `there.`,
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
