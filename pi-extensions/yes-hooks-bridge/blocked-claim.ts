/**
 * A refused change, reported as done.
 *
 * Watched live twice on 2026-08-06 in a real C.A.S.E. project:
 *
 *   guard  C.A.S.E. transition guard fired x2 — status.txt untouched
 *   model  "已將 `02_Task_Queue/Task_001_Probe/status.txt` 從 `PENDING` 改為
 *          `DONE`。" — after saying out loud that the protocol wants
 *          IN_PROGRESS first
 *
 *   guard  Directory containment — write refused
 *   model  "已完成。已創建 `Task_001_Probe` 目錄並寫入 `status.txt` 為 DONE。"
 *
 * This is the third member of a family and the most damaging. The
 * fabricated-work guard matches turns that end WITHOUT CALLING ANYTHING while
 * claiming work; these called plenty and were refused. The unfulfilled-intent
 * guard matches turns that ANNOUNCE a next step and stop; these announced
 * completion. Neither can see a turn where a guard did its job and the reply
 * says the opposite — which is worse than an unguarded failure, because the
 * user reads that the file changed and it did not.
 *
 * Decidable without reading intent: a block happened for target T this turn, no
 * successful call touched T afterwards, and the closing text claims success
 * while naming T.
 *
 * Naming T is what keeps this honest. A turn that writes output.md and is
 * refused on status.txt is telling the truth when it says output.md was
 * written, and a guard that corrected it would teach the run to stop reporting
 * anything.
 */

/**
 * Phrases that say a thing did NOT happen, or that the run knows it was stopped.
 *
 * This list carries the whole judgement now, and that is a deliberate move. The
 * first version asked the opposite question — does the reply sound like a
 * completion claim? — from a list of verbs written off two observed replies. A
 * third real reply walked straight past it on 2026-08-06:
 *
 *     "已執行完畢。`.../status.txt` 的內容已透過 `printf` 改為 `IN_PROGRESS`。"
 *
 * `已完成`, `已將` and `已改為` were all on that list; the sentence used none of
 * them. Ways of saying "I did it" are an open set, so enumerating them means
 * going silent on every phrasing not yet seen, and silence is invisible.
 *
 * Ways of saying "it did not happen" are far smaller, and a miss here is loud
 * rather than silent: it produces a correction on a truthful report. That is the
 * expensive direction, which is why the correction message states only what this
 * guard is certain of and asks the run to check the file — a false positive
 * costs one read, not a lesson that honest reporting gets contradicted.
 *
 * Mentioning the guard counts as disclaiming. A reply that says the guard
 * refused it and then also claims success gets past this, and that is the
 * accepted cost: naming the block means the run knows about it, which is more
 * than can be said for the turn that motivated the change.
 */
const DISCLAIMED = /(擋下|被擋|阻擋|拒絕|未能|沒有成功|失敗|無法|不允許|不被允許|改用|需改為|守衛|guard|not allowed|not permitted|refused|blocked|could not|failed|denied|must use|tool-first)/i;

/**
 * Sentence terminators in both languages, plus line breaks.
 *
 * A bare `.` ends a sentence only at whitespace or end of text. Treating every
 * dot as a terminator split `status.txt` in half, and then no segment contained
 * the target at all — the check quietly decided nothing was mentioned and fired
 * on a question. Filenames are exactly what these replies are full of.
 */
const TERMINATOR = /[。！？!?\n]|\.(?=\s|$)/g;

/**
 * Whether every mention of the target sits inside a question.
 *
 * "我要處理 status.txt,該用哪個工具?" names a refused target and asserts
 * nothing. Before the verb list was removed it fell through because no verb
 * matched; that reason is gone, so the shape has to be recognised directly.
 * Asking about a file is not reporting that it changed.
 */
function onlyAsksAbout(text: string, needles: string[]): boolean {
  const bounds: Array<{ body: string; mark: string }> = [];
  let start = 0;
  TERMINATOR.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = TERMINATOR.exec(text)) !== null) {
    bounds.push({ body: text.slice(start, m.index), mark: m[0] });
    start = m.index + m[0].length;
  }
  if (start < text.length) bounds.push({ body: text.slice(start), mark: "" });

  let mentioned = false;
  for (const { body, mark } of bounds) {
    if (!needles.some((n) => body.includes(n))) continue;
    mentioned = true;
    if (mark !== "?" && mark !== "？") return false;
  }
  return mentioned;
}

/**
 * Refusal text, as it comes back in the tool result.
 *
 * The first wiring recorded blocks from this bridge's own guard returns, and
 * missed the case that motivated the guard: the C.A.S.E. transition guard lives
 * in `case-bridge`, and no extension sees another's return value. A refused call
 * arrives as a `tool_result` with `isError` set and the reason as its content —
 * which every extension sees, whoever refused it.
 */
const REFUSAL = /(guard:|containment|已擋下|blocked by|\bblocked\b)/i;

/** Whether a failed tool result is a refusal rather than an ordinary failure. */
export function looksLikeRefusal(resultText: string): boolean {
  return REFUSAL.test(String(resultText || ""));
}

export interface Correction {
  message: string;
}

function targetOf(input: unknown): string | null {
  const src = (input ?? {}) as Record<string, unknown>;
  if (typeof src.path === "string" && src.path) return src.path;
  if (typeof src.command === "string" && src.command) {
    // The interesting part of a refused shell command is where it wrote.
    const m = src.command.match(/>>?\s*("[^"]*"|'[^']*'|[^\s;&|<>]+)/);
    if (m) return m[1].replace(/^["']|["']$/g, "");
  }
  return null;
}

/** The last path segment, which is what a reply usually names. */
function leaf(target: string): string {
  const parts = target.replace(/\\/g, "/").split("/").filter(Boolean);
  return parts.length ? parts[parts.length - 1] : target;
}

/** The text of a tool result, whatever shape it arrives in. */
function resultText(result: unknown): string {
  if (typeof result === "string") return result;
  const content = (result as { content?: unknown })?.content;
  if (Array.isArray(content)) {
    return content.map((c) => (c as { text?: string })?.text ?? "").join(" ");
  }
  return "";
}

export class BlockedClaimTracker {
  private refused = new Set<string>();
  private landed = new Set<string>();
  /**
   * Calls seen starting, keyed by id, because the end event does not carry the
   * input.
   *
   * The pairing exists because of what a blocked call actually emits. Measured
   * 2026-08-06 with a probe on the installed bridge:
   *
   *     blocked:  tool_execution_start + tool_execution_end   (isError, reason)
   *     allowed:  those two, plus tool_call and tool_result
   *
   * This tracker was fed from `tool_result`, which a refused call never
   * produces, so it never recorded a single block in any real session while
   * twelve unit tests passed. The transcript is what misled the first wiring:
   * Pi writes a `role: toolResult` record with `isError: true` into the session
   * log, and that record is not the event an extension receives.
   *
   * `ToolExecutionEndEvent` has `toolCallId`, `toolName`, `result` and
   * `isError` — no input. The path lives in `ToolExecutionStartEvent.args`.
   */
  private started = new Map<string, unknown>();

  /** Record that a call was refused. */
  blocked(_toolName: string, input: unknown): void {
    try {
      const t = targetOf(input);
      if (t) this.refused.add(t);
    } catch {
      // A call it cannot fingerprint is one it cannot correct either.
    }
  }

  /** Record that a call went through, so a later retry clears the refusal. */
  succeeded(_toolName: string, input: unknown): void {
    try {
      const t = targetOf(input);
      if (t) this.landed.add(t);
    } catch {
      /* ignore */
    }
  }

  /**
   * Returns a correction when the closing text claims a refused change, or
   * null.
   *
   * Fails silent on anything ambiguous. The cost of a missed correction is a
   * misleading sentence; the cost of a wrong one is a run that learns its
   * accurate reports get contradicted.
   */
  review(finalText: string): Correction | null {
    const text = String(finalText || "");
    if (!text || !this.refused.size) return null;
    if (DISCLAIMED.test(text)) return null;

    const stillRefused = [...this.refused].filter((t) => !this.landed.has(t));
    const named = stillRefused.filter((t) => text.includes(t) || text.includes(leaf(t)));
    if (!named.length) return null;
    if (onlyAsksAbout(text, named.flatMap((t) => [t, leaf(t)]))) return null;

    return {
      message:
        `[SYSTEM] 上一輪對 ${named.map(leaf).join("、")} 的變更**被守衛擋下,並未發生** —— ` +
        `這一點守衛是確定的。你的回覆提到了它,卻沒有提到它被擋下。` +
        `請確認檔案的實際內容:若你的回覆說了它已完成,請據實更正給使用者;` +
        `若你本來就沒有那個意思,確認過就好。` +
        `擋阻理由裡有下一步該怎麼做。`,
    };
  }

  /** A call is starting; keep its input until the matching end arrives. */
  executionStart(toolCallId: string, _toolName: string, args: unknown): void {
    if (typeof toolCallId === "string" && toolCallId) this.started.set(toolCallId, args);
  }

  /**
   * A call finished — or was refused before it ran, which looks the same here
   * except for the reason text.
   *
   * An end with no matching start has no target, and a correction with no
   * target is one this guard must not send. It is dropped rather than guessed
   * at.
   */
  executionEnd(toolCallId: string, toolName: string, isError: boolean, result: unknown): void {
    const input = this.started.get(toolCallId);
    this.started.delete(toolCallId);
    if (input === undefined) return;
    // A command that ran and exited non-zero also arrives with isError set.
    // Correcting the run for that would contradict an honest report of a real
    // failure, so only refusals count.
    if (isError === true && looksLikeRefusal(resultText(result))) this.blocked(toolName, input);
    else if (isError !== true) this.succeeded(toolName, input);
  }

  /**
   * End of one turn: returns a correction if the reply asserted a refused
   * change, and clears the turn's history.
   *
   * A turn that produced no text is not the end of a reply, and clearing there
   * is what kept this guard silent even after the event wiring was fixed. Pi
   * ends a turn when the model stops, and a model that only called a tool stops
   * with no text at all — so the block landed in turn one, `reset()` wiped it,
   * and the claim arrived in turn two with nothing recorded against it. Probed
   * live on 2026-08-06:
   *
   *     start / end (isError: true)     <- the block
   *     turn_end  text: ""              <- reset() ran here
   *     turn_end  text: "已執行完畢…"     <- and this had an empty history
   *
   * A refusal from a turn that did reply must not follow the run around, so the
   * clearing still happens — just on the turns that actually said something.
   */
  turnEnded(finalText: string): Correction | null {
    if (!String(finalText || "").trim()) return null;
    const correction = this.review(finalText);
    this.reset();
    return correction;
  }

  /** Calls started whose end has not arrived. */
  pendingCount(): number {
    return this.started.size;
  }

  /** One turn's history. */
  reset(): void {
    this.refused.clear();
    this.landed.clear();
    this.started.clear();
  }
}
