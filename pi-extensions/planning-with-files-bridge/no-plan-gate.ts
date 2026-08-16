/**
 * The case this bridge is named after, and the only one it never handled.
 *
 * Every handler in index.ts opens with a variant of `if (!hasAnyPlan(cwd))
 * return;` — before_agent_start, tool_result and turn_end alike. So the
 * planning bridge helps sessions that ALREADY plan, and has nothing to say to
 * the ones that do not. That is the owner's actual complaint
 * (「我抱怨的是他沒有先規劃就開始」) and, measured 2026-08-16 across 41 real
 * sessions that searched at least once:
 *
 *     plan-first     5   12.2%
 *     search-first   2    4.9%
 *     no-plan       34   82.9%
 *     of the sessions with 20+ tool calls, 11 of 18 had no plan file at all
 *
 * Nobody noticed because every check asked "did the bridge deliver its
 * injection", never "did it reach the case it exists for".
 *
 * WHY A REFUSAL AND NOT ADVICE. This repo has measured both. Skill text and
 * routing notes lose to the moment of action — reshaping the same instruction
 * into a table column was ignored 3/3 — and the one thing that ever moved a
 * number here was a tool_call refusal (URLs in files 0 -> 10).
 *
 * WHY IT REFUSES A WRITE AND NOT A SEARCH. The phase gate refused searches and
 * took premature searches from 15 to 0 and REAL research from 15 to 0 in the
 * same run: it removed the only road. The citation gate refused the
 * DELIVERABLE instead, and worked. This copies the citation gate: the road
 * (searching, reading, running commands) stays open, and the thing held back is
 * the first durable artifact — for which the escape is itself a write, so the
 * gate cannot deadlock. Writing `task_plan.md` satisfies it, in-band, in one
 * call, using a tool the model already has open.
 *
 * WHAT IT DOES NOT CLAIM. That a plan file makes the work better. It makes the
 * plan exist and visible, which is the thing that was asked for and the thing
 * report-plan-order.py counts. Whether the outcome improves is not established
 * and must not be asserted from this.
 */

/**
 * Calibration, not protocol — and calibrated from session shapes rather than
 * chosen. Measured 2026-08-16 over 75 real sessions that made any tool call:
 *
 *     length     median 15, p75 43, p90 168
 *     buckets    1-4: 20   5-11: 16   12-19: 3   20+: 36
 *     36 sessions ever wrote a file; FIRST write at call:
 *                median 17, p25 8, p75 22
 *     first-write buckets   1-4: 7   5-11: 4   12-19: 9   20+: 16
 *
 * At 12, the gate can reach the 25 of 36 writing sessions (69%) whose first
 * durable artifact lands at call 12 or later, and stays out of the 11 that write
 * within the first eleven calls — quick edits and one-file answers, where
 * demanding a plan would be pure friction.
 *
 * The first live probe never reached it: that session ended at 10 calls, so the
 * gate could not fire and nothing about it was tested. Recorded because "it did
 * not fire" and "it does not work" are different statements and this repo has
 * confused them before.
 */
export const MIN_CALLS_BEFORE_GATE = 12;

/** One refusal, then never again. Consecutive identical refusals are how the
 * depth guard spoke three times while the model issued twenty more searches;
 * repeating a message the model already declined teaches nothing and costs a
 * turn each time. */
export const MAX_GATE_REFUSALS = 1;

/** Filenames that ARE a plan, so writing one is never blocked. Kept in step with
 * PLANNING_FILES in index.ts; a plan under any of these names satisfies
 * hasAnyPlan or is the direct path to it. */
const PLAN_NAMES = ["task_plan.md", "plan.md", "findings.md", "progress.md"];

/** Artifacts too trivial to be worth a plan, or produced BY tooling rather than
 * by the work. Refusing these would be pure friction. */
const EXEMPT = [
  /(^|[\\/])\.[^\\/]+$/,           // dotfiles: .gitignore, .env
  /\.(json|lock|log|tmp|png|jpe?g|svg|ico|zip)$/i,
  /(^|[\\/])(readme|license|changelog)\.md$/i,
];

export function isPlanFile(path: string): boolean {
  const base = path.replace(/\\/g, "/").split("/").pop()?.toLowerCase() ?? "";
  return PLAN_NAMES.includes(base);
}

export function isExempt(path: string): boolean {
  const p = path.replace(/\\/g, "/");
  return EXEMPT.some((re) => re.test(p));
}

export interface NoPlanRefusal {
  block: true;
  reason: string;
}

/**
 * Counts the work and decides. Deliberately a class with explicit state rather
 * than module-level counters: `ecc-hooks-bridge` cannot be imported under bare
 * node and its handler logic was untestable for exactly that reason, so
 * anything here that can be wrong lives where a test can call it.
 */
export class NoPlanGate {
  private calls = 0;
  private refusals = 0;
  private readonly minCalls: number;
  private readonly maxRefusals: number;

  // Plain fields, not constructor parameter properties: Node's type stripping
  // erases annotations without transforming, so the parameter-property form is
  // ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX and the module never loads. Enforced by
  // tests/test_bridge_ts_syntax.py.
  constructor(minCalls = MIN_CALLS_BEFORE_GATE, maxRefusals = MAX_GATE_REFUSALS) {
    this.minCalls = minCalls;
    this.maxRefusals = maxRefusals;
  }

  /** Every tool call in the session, whatever it is. The threshold is about how
   * much work has happened, not how much of one kind. */
  observe(): void {
    this.calls += 1;
  }

  /**
   * `null` to allow. A refusal only when: enough work has already happened, the
   * call is a write of a durable artifact, no plan exists, and this gate has
   * not spoken yet.
   *
   * `planExists` is passed in rather than read here so the caller owns the
   * filesystem and the decision stays testable without one.
   */
  check(toolName: string, path: unknown, planExists: boolean): NoPlanRefusal | null {
    if (planExists) return null;
    if (this.refusals >= this.maxRefusals) return null;
    if (this.calls < this.minCalls) return null;
    if (toolName !== "write" && toolName !== "edit") return null;
    if (typeof path !== "string" || !path) return null;
    if (isPlanFile(path) || isExempt(path)) return null;

    this.refusals += 1;
    return {
      block: true,
      reason:
        `這個 session 已經做了 ${this.calls} 次工具呼叫,而工作目錄裡還沒有 ` +
        `task_plan.md。現在要寫的是 \`${path}\` —— 一份沒有計畫在前面的產出,` +
        `之後沒有人(包括你自己)能說出它為什麼長這樣。\n\n` +
        `先寫 task_plan.md,再寫這個檔案。**一行就夠**:目標是什麼、分成哪幾步、` +
        `現在在第幾步。不需要格式,不需要完整,寫完就繼續。\n\n` +
        `這是這個 session 唯一一次這樣擋你;寫不寫由你決定,但這一次請先寫。`,
    };
  }

  stats(): { calls: number; refusals: number } {
    return { calls: this.calls, refusals: this.refusals };
  }
}
