/**
 * Putting the original request back in front of the model, mid-run.
 *
 * The owner's question was the whole reason this exists: "跑到第 18 步還記得:
 * 我原本到底要完成什麼?" Checked on 2026-08-09, the harness had no answer.
 * Everything carrying the goal — the Constitution, the Roadmap, the verifiability
 * block, this bridge's own routing note — is injected at `before_agent_start`,
 * and the installed type declares that as "Fired after user submits prompt but
 * before agent loop". Once per USER MESSAGE. Session 019fe60f was one user
 * message and sixteen assistant turns: the goal was stated at turn 0 and never
 * again.
 *
 * Every other mechanism in this harness is wired to tool_call/tool_result/turn_end
 * and answers "is this step allowed". Drift asks "am I still doing the right
 * thing". This is the first thing here that answers the second question.
 *
 * Design ported from `research/oh-my-pi-can1357`'s mid-run todo nudge
 * (`src/session/todo-tracker.ts:287`), which had already solved the shape:
 *
 *   - count ACTIONS, not turns, so a short exchange is never interrupted;
 *   - a hard per-cycle cap, because rarity is what keeps it from becoming
 *     wallpaper the model learns to skip;
 *   - reset per prompt cycle;
 *   - evaluate at injection time, not when the counter trips.
 *
 * Not ported: its carrier. That project forks pi's core and can `appendMessage`.
 * An extension has exactly one channel measured to reach the model mid-run — a
 * `tool_result` handler returning `{ content: [...existing, block] }` — so the
 * restatement rides a tool result, the same way `case-bridge/phase-notice.ts`
 * does.
 *
 * The threshold is calibrated, not chosen. Across 219 real user-prompt cycles on
 * this machine, tool calls per cycle are bimodal: median 2, p75 18, p90 38, max
 * 811. Twelve leaves short cycles silent and fires on 32.4% of real ones.
 *
 * Measurement plan, written before this file existed:
 * `docs/measurements/2026-08-09-task019-preregistration.md`.
 */

/**
 * Successful tool calls in one cycle before the goal is restated.
 *
 * Counts EVERY successful call, not a "mutating" subset. The 32.4% figure above
 * was measured over all tool calls, and counting a subset here would silently
 * invalidate the calibration it came from.
 */
export const RESTATE_THRESHOLD = 12;

/** Restatements per prompt cycle. Rarity is the design, not a limitation. */
export const MAX_RESTATEMENTS = 2;

/** How much of the request rides along. It shares space with a tool result. */
export const MAX_GOAL_CHARS = 400;

/** Label it, so it is never mistaken for what the tool printed. */
const HEADER = "[task-shape] 目標重述(不是指令輸出):";

/** Collapse whitespace so a multi-line prompt does not swamp the result. */
function condense(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

/**
 * The request, shortened from the front.
 *
 * The head is kept rather than the tail because a request states what it wants
 * first and qualifies it afterwards. Truncation is marked: a silently clipped
 * goal reads as a complete one, and a model acting on half a request is the
 * failure this file exists to prevent.
 */
export function shorten(prompt: string, max = MAX_GOAL_CHARS): string {
  const one = condense(prompt);
  if (one.length <= max) return one;
  return one.slice(0, max) + " …(原文更長,已截斷)";
}

/**
 * The restatement itself.
 *
 * Three things and no more: what was asked, how far in we are, and one question.
 * It ends on a question rather than an instruction on purpose — an instruction
 * here is another rule among many, and this repo has measured three times over
 * that added rules get skipped while a demand for an answer does not. The count
 * is included because how far in it is, is the part the model cannot observe
 * about itself.
 *
 * It says RESULTS, not calls, and the distinction came out of the first live run
 * rather than out of design. Session 019fe72a fired on the 12th result while the
 * model had already issued 14 calls — turns emit tool calls in batches (2/4/4/4/
 * 4/1/1 there), so the two numbers diverge. Telling a model "you have made 12
 * calls" when it can see 14 puts a false statement inside the one message whose
 * whole job is to be the reliable account of where it is.
 */
export function restatement(goal: string, acts: number): string {
  return (
    `${HEADER}\n` +
    `使用者這一輪原本要的是:「${goal}」\n` +
    `到目前為止已經有 ${acts} 次工具結果回來(批次發出的呼叫數可能更多)。` +
    `在繼續之前,請先確認你現在做的事仍然在回答上面這句話 —— ` +
    `如果已經偏開,現在說出來並修正方向,不要等到最後才發現。`
  );
}

/**
 * Per-cycle state for one session.
 *
 * A class rather than module-level counters because `session_start` and
 * `before_agent_start` both have to reset it, and this repo has been bitten by
 * per-turn state cleared in the wrong place (`turn_end` fires on turns that
 * produced no text).
 */
export class GoalRestate {
  private goal: string | null = null;
  private acts = 0;
  private sent = 0;

  /**
   * Start a prompt cycle. Arms only for multi-step requests.
   *
   * A single-step request cannot drift from itself, and this bridge already
   * decides multi-step for its routing note — reusing that decision rather than
   * inventing a second one, after building a duplicate classifier once already.
   */
  begin(prompt: unknown, multiStep: boolean): void {
    this.acts = 0;
    this.sent = 0;
    const text = typeof prompt === "string" ? condense(prompt) : "";
    this.goal = multiStep && text ? shorten(text) : null;
  }

  /**
   * Text to append to this tool result, or null.
   *
   * Errors do not count. A refused or failed call is not progress, and counting
   * it would make a struggling run — the one least able to use a reminder as
   * anything but noise — the one that gets interrupted soonest.
   */
  afterToolResult(isError: unknown): string | null {
    if (!this.goal) return null;
    if (isError === true) return null;
    this.acts++;
    if (this.acts < RESTATE_THRESHOLD) return null;
    if (this.sent >= MAX_RESTATEMENTS) return null;
    this.sent++;
    const text = restatement(this.goal, this.acts);
    this.acts = 0;
    return text;
  }

  /**
   * Disarm for the rest of the session, until the next `begin()`.
   *
   * Only the goal is cleared. The counters are not: `afterToolResult` returns on
   * a null goal before reading them, and `begin()` zeroes both. The first
   * version cleared all three, and the mutation sweep survived changing either
   * counter here — an unobservable assignment is a line to delete, not a line to
   * write a test for.
   *
   * An `armed()` accessor lived here too, written "for tests and the status
   * line" and called by neither. Two of the sweep's survivors were inside it.
   * Same disposal as `ScopeSnapshot.taken`.
   */
  reset(): void {
    this.goal = null;
  }
}
