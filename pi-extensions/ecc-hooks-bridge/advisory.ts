/**
 * Advisories the model can actually read.
 *
 * This bridge ran seven hook sites whose findings were delivered with
 * `ctx.ui.notify`. That paints the terminal and stops there — the model never
 * received a character of it, so quality-gate could report a broken edit and the
 * model would keep building on it. Checked against the installed runtime, not the
 * frozen fork under `reference/oh-my-pi` (0.73-era, missing fields 0.83.0 has):
 *
 *   @earendil-works/pi-coding-agent@0.83.0 dist/core/extensions/types.d.ts
 *     :778  ToolCallEventResult  { block?; reason?; }        <- no other exit
 *     :790  ToolResultEventResult{ content?; details?; ... }
 *     :876  on("turn_end", ExtensionHandler<TurnEndEvent>)   <- no result at all
 *   @earendil-works/pi-agent-core  dist/types.d.ts:310
 *     AgentToolResult.content  "returned to the model"
 *     AgentToolResult.details  "for logs or UI rendering"
 *
 * Two consequences shape this file. `content` on a tool result is the only
 * channel a hook has to the model. And `turn_end` has no channel, so a finding
 * produced there has to wait for the next event that does — hence a queue rather
 * than a formatting helper.
 *
 * The queue is per extension instance, which is per session.
 */

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

/** How often a given key is allowed to reach the model. */
export type AdvisoryPolicy = "once" | "always" | { cooldown: number };

interface PendingAdvisory {
  key: string;
  text: string;
}

/** Prefix every block, so an advisory is never mistaken for command output. */
export const ADVISORY_HEADER = "[ecc-hooks] advisory (not command output):";

/**
 * Default per-drain ceiling. Drains ride along on tool results, so this is paid
 * on tool calls that have something pending, every time.
 */
export const DEFAULT_DRAIN_BUDGET = 1200;

const TRUNCATION_MARK = " …[truncated]";

/**
 * Whether hook findings are allowed to reach the model at all.
 *
 * They enter the model's context, and this harness is tuned for a weak local
 * model — a 42,999-char tool result was observed derailing that exact model, which
 * is why stealth-web-bridge and deep-research-bridge truncate. The drain budget is
 * far below that, but if the model does get pulled off course the operator needs a
 * switch that does not require editing source and reinstalling.
 *
 * Fails open, like `planningBridgeEnabled()` in planning-with-files-bridge: an
 * unreadable config must not silently remove a guard.
 */
export function hookAdvisoriesEnabled(harnessRoot: string): boolean {
  try {
    const cfgPath = join(harnessRoot, "pi-config", "harness-config.json");
    if (!existsSync(cfgPath)) return true;
    const cfg = JSON.parse(readFileSync(cfgPath, "utf8"));
    return cfg["enableHookAdvisories"] !== false;
  } catch {
    return true;
  }
}

export class AdvisoryQueue {
  private pending: PendingAdvisory[] = [];
  private drainCount = 0;
  private firedOnce = new Set<string>();
  private lastPushedAt = new Map<string, number>();
  private readonly enabled: boolean;

  /**
   * One decision covers all eight producers. Gating each call site instead would
   * be eight chances to miss one.
   */
  constructor(options?: { enabled?: boolean }) {
    this.enabled = options?.enabled !== false;
  }

  /**
   * Offer an advisory. Returns whether the policy let it through, so callers can
   * skip the work of building a message that would have been dropped.
   */
  push(key: string, text: string, policy: AdvisoryPolicy = "always"): boolean {
    if (!this.enabled) return false;
    const body = (text ?? "").trim();
    if (!body) return false;

    if (policy === "once") {
      if (this.firedOnce.has(key)) return false;
      this.firedOnce.add(key);
    } else if (typeof policy === "object" && policy !== null) {
      const last = this.lastPushedAt.get(key);
      if (last !== undefined && this.drainCount - last <= policy.cooldown) return false;
    }

    this.lastPushedAt.set(key, this.drainCount);
    this.pending.push({ key, text: body });
    return true;
  }

  /**
   * Take as much as fits, leaving the rest for the next tool result. Returns null
   * when there is nothing to say — callers use that to leave the tool result
   * untouched instead of rewriting it with an empty block.
   */
  drain(budget: number = DEFAULT_DRAIN_BUDGET): string | null {
    this.drainCount++;
    if (this.pending.length === 0) return null;

    const taken: string[] = [];
    let used = ADVISORY_HEADER.length;

    while (this.pending.length > 0) {
      const next = this.pending[0];
      const cost = next.text.length + 1;
      // An advisory larger than the whole budget is still worth saying. Dropping
      // it silently is how a guard fires zero times and nobody finds out.
      if (taken.length > 0 && used + cost > budget) break;
      taken.push(next.text);
      used += cost;
      this.pending.shift();
    }

    const block = `${ADVISORY_HEADER}\n${taken.join("\n")}`;
    if (block.length <= budget) return block;
    return block.slice(0, Math.max(0, budget - TRUNCATION_MARK.length)) + TRUNCATION_MARK;
  }

  get pendingCount(): number {
    return this.pending.length;
  }

  /**
   * Forget everything, for a new session.
   *
   * Pi invokes an extension's default export once per process but fires
   * `session_start` once per session, so after `/new` this same queue is still
   * holding the previous session's history: a `once` advisory would never fire
   * again, and a finding about edits nobody in the new session made would be
   * handed over as if it were current.
   */
  reset(): void {
    this.pending = [];
    this.drainCount = 0;
    this.firedOnce.clear();
    this.lastPushedAt.clear();
  }
}

type TextBlock = { type: "text"; text: string };

/**
 * Build the value a tool_result handler returns, or null when it should return
 * nothing at all.
 *
 * Two things are easy to get wrong here, and the first wiring got both. The
 * result is an object with a `content` field — returning the bare array made Pi
 * drop the advisory silently, with every unit test still green and only the
 * session log showing the tool result unchanged. And `content` REPLACES the
 * result, so the advisory is appended to what the tool produced; returning it
 * alone would delete the command's own output.
 */
export function advisoryResult(
  content: readonly unknown[] | undefined,
  advisory: string | null | undefined,
): { content: unknown[] } | null {
  if (!advisory) return null;
  const existing = Array.isArray(content) ? [...content] : [];
  const block: TextBlock = { type: "text", text: advisory };
  return { content: [...existing, block] };
}
