/**
 * The audit trail, written by the harness rather than asked for.
 *
 * C.A.S.E. requires `action_log.jsonl` — one JSON object per tool call — and
 * until 2026-08-06 the verifier only warned when it was missing, which made it
 * optional in practice. The deeper problem is not the severity: it is that the
 * agent under audit was being asked to keep its own audit trail. Session
 * 019fd29d made 40 tool calls and wrote no files at all.
 *
 * The harness sees every tool call already. Writing the log here needs no
 * cooperation, cannot be forgotten, and cannot be skipped under load — the
 * three ways the previous arrangement failed.
 *
 * Two limits, both deliberate:
 *
 *   Exactly one task open. With none, there is no task the call belongs to.
 *   With two, guessing files the evidence under the wrong task, which is worse
 *   than not filing it — and the queue guard is already refusing that state.
 *
 *   Arguments are summarised, never copied. A log embedding the content of
 *   every write is a second copy of the deliverable, and `output.md` is the
 *   deliverable.
 */

import { appendFileSync, existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

const TASK_DIR_RE = /^Task_(\d+)_/;
const QUEUE_DIR = "02_Task_Queue";

/** Where the reference workspace keeps its queue, besides the project root. */
const NESTED_ROOTS = ["C.A.S.E._Framework"];

/** Argument fields worth keeping, per tool, in the order they are checked. */
const SUMMARY_FIELDS = ["path", "command", "query", "url", "pattern"];

/** Long enough to identify a call, short enough that the log stays readable. */
const MAX_FIELD_CHARS = 256;

function clip(value: unknown): string | null {
  if (typeof value !== "string" || !value) return null;
  return value.length > MAX_FIELD_CHARS ? value.slice(0, MAX_FIELD_CHARS) + "…" : value;
}

/**
 * The part of a call worth recording.
 *
 * Allow-listed rather than filtered: an unknown tool contributes only the
 * fields named above, so a tool that carries a credential or a whole file in
 * some other argument cannot leak it into a file that lives in the repository.
 */
export function summarizeInput(_toolName: string, input: unknown): Record<string, string> {
  const src = (input ?? {}) as Record<string, unknown>;
  const out: Record<string, string> = {};
  for (const field of SUMMARY_FIELDS) {
    const value = clip(src[field]);
    if (value !== null) out[field] = value;
  }
  return out;
}

function statusOf(taskDir: string): string | null {
  try {
    return readFileSync(join(taskDir, "status.txt"), "utf8").trim();
  } catch {
    return null;
  }
}

function queueDirsFor(cwd: string): string[] {
  return [join(cwd, QUEUE_DIR), ...NESTED_ROOTS.map((n) => join(cwd, n, QUEUE_DIR))];
}

/**
 * The single task directory at IN_PROGRESS, or null.
 *
 * Null covers three different situations on purpose — no queue, no open task,
 * more than one open task — because the response to all three is the same: do
 * not write anything.
 */
export function findActiveTask(cwd: string): string | null {
  for (const queue of queueDirsFor(cwd)) {
    if (!existsSync(queue)) continue;
    let open: string[];
    try {
      open = readdirSync(queue)
        .filter((n) => TASK_DIR_RE.test(n))
        .filter((n) => statusOf(join(queue, n)) === "IN_PROGRESS")
        .map((n) => join(queue, n));
    } catch {
      continue;
    }
    if (open.length === 1) return open[0];
  }
  return null;
}

export class ActionLogger {
  /**
   * Appends one line for a call that actually ran, and returns the file it was
   * written to — or null when there was nowhere to put it.
   *
   * Never throws. An audit trail that can break a turn is worse than no audit
   * trail, because it turns a bookkeeping problem into a stopped session.
   */
  record(cwd: string, toolName: string, input: unknown, isError: boolean): string | null {
    try {
      const taskDir = findActiveTask(cwd);
      if (!taskDir) return null;
      const entry: Record<string, unknown> = {
        at: new Date().toISOString(),
        tool: String(toolName || "unknown"),
        ...summarizeInput(toolName, input),
      };
      if (isError) entry.error = true;
      const target = join(taskDir, "action_log.jsonl");
      appendFileSync(target, JSON.stringify(entry) + "\n", "utf8");
      return target;
    } catch {
      return null;
    }
  }
}
