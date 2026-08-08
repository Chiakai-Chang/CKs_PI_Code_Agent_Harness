/**
 * The human saying "pass", read from what the human actually typed.
 *
 * C.A.S.E. Section 7 offers two approval routes, and this harness had
 * implemented only the second:
 *
 *   Path A — Human-in-the-Loop, "default for supervised/interactive
 *   deployments". The human approves in natural language in the chat and the
 *   agent translates that into the state change.
 *
 *   Path B — Autonomous Checker, for continuous/unattended execution, which
 *   does require a fresh context.
 *
 * Section 1 says only that "a Worker MUST NOT self-approve its own output as
 * final". In Path A the Checker is the person, so their "pass" satisfies
 * dual-track outright — nothing asks for a second session. The advancer was
 * telling users to open one anyway, and the queue guard refused REVIEW -> DONE
 * from the session that had claimed the task, which made Path A unexecutable.
 * "Worker must not self-approve" had been read as "must change session".
 *
 * The evidence may only be a real user prompt. `before_agent_start` carries
 * `prompt: string` — "The raw user prompt text (after expansion)" — and the
 * bridge reads it directly. Nothing the model says counts: `blocked-claim`
 * measured a run reporting "已執行完畢" for a call that had been refused.
 */

/** Our own injected text, which must never read as the user speaking. */
const OURS = /^\s*\[(C\.A\.S\.E\.|SYSTEM)\]/i;

/**
 * Approval is short and deliberate. A paragraph that happens to contain "OK"
 * is a paragraph; treating it as consent is how a guard invents permission.
 */
const MAX_APPROVAL_CHARS = 40;

/**
 * Anything asking for more work. Checked before approval, never after.
 *
 * `問題` alone was here and it rejected `沒問題` — the exact phrase
 * for_humans.md gives as an example of approval. A rejection list wide enough
 * to swallow the protocol's own approval word is a list that would have made
 * Path A unusable a second time, differently.
 */
const REJECTION = /(改|修正|不行|不要|還沒|還有|沒有通過|不通過|還不能|再看|再想|有問題|fix|change|needs? work|don'?t|reject|\bnot\b)/i;

/** A question is the user asking, not the user deciding. */
const QUESTION = /[?？]|嗎|可以.*了嗎|is it|can i/i;

/**
 * Approval phrases. The first four are named outright in Section 7 and the two
 * Chinese ones in for_humans.md 步驟三; the rest are the ordinary ways the same
 * decision gets typed.
 */
const APPROVAL_ASCII = /(^|[\s,.!])(pass|looks good|approved?|ok|okay|lgtm|ship it)([\s,.!]|$)/i;
/**
 * Chinese needs no delimiters, and requiring them was the first version's bug:
 * `可以通過` failed because `通` follows `以` with no space, which is how the
 * language works.
 */
const APPROVAL_CJK = /(通過|沒問題|收工|結案|同意)/;

/**
 * Whether a user prompt is an approval.
 *
 * Deliberately hard to satisfy. A false negative costs the user one more
 * sentence; a false positive marks unfinished work as accepted and moves the
 * queue past it, and nothing downstream reopens a closed task.
 */
export function isHumanApproval(prompt: unknown): boolean {
  const text = String(prompt ?? "").trim();
  if (!text || text.length > MAX_APPROVAL_CHARS) return false;
  if (OURS.test(text)) return false;
  if (QUESTION.test(text)) return false;
  if (REJECTION.test(text)) return false;
  return APPROVAL_ASCII.test(text) || APPROVAL_CJK.test(text);
}

/**
 * One approval, spendable once.
 *
 * Without consumption a single "OK" would keep closing every task after it —
 * the same state-crossing-a-boundary defect that kept `blocked-claim` silent
 * for a day, where a tool-only turn cleared history before the turn that
 * actually spoke.
 */
export class ApprovalRecord {
  private pending = false;

  /** Called with each raw user prompt. */
  note(prompt: unknown): void {
    if (isHumanApproval(prompt)) this.pending = true;
  }

  /** Consume the approval, if there is one. */
  take(): boolean {
    const had = this.pending;
    this.pending = false;
    return had;
  }

  reset(): void {
    this.pending = false;
  }
}
