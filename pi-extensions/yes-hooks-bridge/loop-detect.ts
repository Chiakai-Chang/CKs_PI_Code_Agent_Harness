/**
 * The loop that cycles, which the consecutive guard cannot see.
 *
 * Measured 2026-08-05 on one run of a market-survey brief: 598 `web_search`
 * calls, 43 distinct queries, each repeated about 44 times. Twenty-five minutes,
 * then a timeout. `repeatCallGuard` in index.ts stayed silent the whole way, and
 * its own comment explains why:
 *
 *   // Consecutive only: any different call resets the count, so
 *   // edit/test/edit/test cycles — identical `bash` calls separated by real
 *   // work — are untouched.
 *
 * Every call differed from the one before it, so the counter reset 598 times.
 * That guard sees AAAA. This one sees ABCABCABC.
 *
 * A sliding window would not have worked either: 43 distinct queries spread
 * across any reasonable window leave each signature appearing once or twice.
 * What does hold is that an identical search returns identical results — issuing
 * it a sixth time cannot produce information the first five did not. So the
 * tally is per signature, for the whole session.
 *
 * Only for tools where that reasoning holds. `bash`, `edit` and `write` repeat
 * legitimately, because the file changed in between; that is the case the
 * consecutive guard was careful to protect and this must not undo it.
 */

/**
 * Tools whose identical call cannot yield new information.
 *
 * A search returns what the index holds; a page returns what it served. Reading
 * a file again is different — something may have written it.
 */
const IDEMPOTENT_LOOKUPS = new Set(["web_search", "web_open", "deep_research"]);

/**
 * How many times one query may be issued before it is refused.
 *
 * Generous: five identical searches is already four more than useful. The real
 * loop ran forty-four rounds.
 */
export const SAME_QUERY_LIMIT = 5;

export interface CycleBlock {
  block: true;
  reason: string;
}

export class CycleDetector {
  private tally = new Map<string, number>();

  /**
   * Returns a block for a lookup that has already been made too many times,
   * or null.
   *
   * Fails open on anything it cannot fingerprint: a call it cannot describe is
   * a call it has no business refusing.
   */
  check(toolName: string, input: unknown): CycleBlock | null {
    if (!IDEMPOTENT_LOOKUPS.has(String(toolName || "").toLowerCase())) return null;

    let signature: string;
    try {
      signature = `${toolName}:${JSON.stringify(input ?? {})}`;
    } catch {
      return null;
    }

    const count = (this.tally.get(signature) ?? 0) + 1;
    this.tally.set(signature, count);
    if (count <= SAME_QUERY_LIMIT) return null;

    return {
      block: true,
      reason:
        `Repeat-lookup guard: this exact \`${toolName}\` has now been issued ` +
        `${count} times and returns the same thing every time. Searching again ` +
        `with different words is what turned one run into 598 searches and a ` +
        `timeout. Call web_open on one of the addresses the results already gave ` +
        `you, or say in plain text what you could not find.`,
    };
  }

  /** A new session starts with no history. */
  reset(): void {
    this.tally.clear();
  }
}
