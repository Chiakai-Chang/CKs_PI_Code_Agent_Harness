/**
 * Saying when the door opened, because closing it was the only thing measured.
 *
 * 2026-08-08, the 4b research run. The turn-based exit ramp worked exactly as
 * designed: twenty refusals across four turns, one voice per turn, and zero
 * successful searches before the task was claimed — down from fifteen.
 *
 * Then the model claimed the task and never searched again. Twelve turns of
 * bash, read and write, no `web_search`, although research is wide open in the
 * PLAN phase. It wrote its reasoning into its own deliverable: "web_search
 * 工具被 C.A.S.E. 框架攔截,以下版本號來自知識庫,可能已過時."
 *
 * That generalisation was rational. It had seen twenty refusals and zero
 * permissions. The owner had said plainly that searching more is good and only
 * the ordering was wrong, so premature searches 15 -> 0 was the win and real
 * research 15 -> 0 was the bill.
 *
 * Third appearance of this shape (citation gate: URLs 0 -> 10 and fabricated
 * ones 0 -> 4; phase gate v1: refusals fired and status never left PENDING).
 * The sharp version is not "a threshold defines the shape of the evasion" —
 * nothing was evaded here, the capability was dropped:
 *
 *   **A guard that removes an option must be paired with something that
 *   speaks when the option comes back.**
 *
 * The carrier cannot be the advancer: it speaks only on a turn that produced
 * text and called no tools, and turns 6 to 15 all called tools, so the notice
 * would have landed at turn 16. It rides the tool result of the claim itself —
 * one of the two channels measured to reach the model here, and the moment the
 * statement becomes true.
 */

import { basename, dirname, join, resolve } from "node:path";
import { existsSync, readFileSync } from "node:fs";
import { bashWriteTargets } from "./task-queue-guard.ts";

/** The written targets of a call, whichever tool made it. */
function writeTargets(toolName: string, input: unknown): string[] {
  const src = (input ?? {}) as Record<string, unknown>;
  if (toolName === "bash") return bashWriteTargets(String(src.command ?? ""));
  if (toolName === "write" || toolName === "edit") {
    const p = src.path ?? src.file_path;
    return typeof p === "string" && p ? [p] : [];
  }
  return [];
}

function statusOf(taskDir: string): string {
  try {
    return readFileSync(join(taskDir, "status.txt"), "utf8").trim().toUpperCase();
  } catch {
    return "";
  }
}

/**
 * The message itself.
 *
 * Short on purpose: it rides a tool result the model is already reading, and a
 * paragraph there competes with the result. It names the tool that was
 * refused, because that is the belief being corrected — "you are now in PLAN"
 * is a status line, and the run that produced this needed to be told it may
 * search again, in those words.
 */
const OPENED =
  "[C.A.S.E.] 認領完成,階段閘已經放開 —— **`web_search` / `web_open` 從現在起不會再被擋**。" +
  "剛才擋你的是「還沒認領就開工」,不是搜尋本身。現在請盡量搜、盡量查證," +
  "不要用記憶作答。";

/**
 * The task directory a successful call just moved into IN_PROGRESS, or null.
 *
 * Extracted from `PhaseNotice.afterToolResult` when the task-local constitution
 * needed the same moment. Two detectors for one event would drift apart the way
 * `uninstall.py` and `restore.py` did — one managed five bridges while the other
 * managed eleven, and seven kept loading forever.
 */
export function claimedTaskDir(
  queueDir: unknown,
  toolName: unknown,
  input: unknown,
  isError: unknown,
): string | null {
  // A refused call claimed nothing, so nothing opened.
  if (isError === true) return null;
  const queue = String(queueDir ?? "");
  if (!queue || !existsSync(queue)) return null;

  for (const target of writeTargets(String(toolName ?? ""), input)) {
    let abs: string;
    try {
      abs = resolve(target);
    } catch {
      continue;
    }
    if (basename(abs).toLowerCase() !== "status.txt") continue;
    const taskDir = dirname(abs);
    if (resolve(dirname(taskDir)) !== resolve(queue)) continue;
    // Read the file rather than trusting the arguments: `bash` writes carry no
    // extractable content, and the point is what the task IS now, not what the
    // call said it would be.
    if (statusOf(taskDir) !== "IN_PROGRESS") continue;
    return taskDir;
  }
  return null;
}

export class PhaseNotice {
  /** Task directories already told. Once is the whole design. */
  private told = new Set<string>();

  /**
   * A line to append to this tool result, or null.
   *
   * Fires only when a write that just succeeded moved a task out of CLAIM.
   * Everything else stays silent — a notice on every status write becomes the
   * wallpaper the model already learned to skip.
   */
  afterToolResult(
    queueDir: unknown,
    toolName: unknown,
    input: unknown,
    isError: unknown,
  ): string | null {
    const taskDir = claimedTaskDir(queueDir, toolName, input, isError);
    if (!taskDir) return null;
    if (this.told.has(taskDir)) return null;
    this.told.add(taskDir);
    return OPENED;
  }

  reset(): void {
    this.told.clear();
  }
}
