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

/** Phrases that assert something was done. Both languages, because both appear. */
const CLAIM = /(已完成|已將|已把|已寫入|已建立|已創建|已更新|已修改|已改為|已改成|完成了|\bdone\b|\bupdated\b|\bcreated\b|\bwrote\b|\bwritten\b|\bchanged\b|\bset to\b|successfully)/i;

/**
 * Phrases that say a thing did NOT happen. Checked first: a truthful report of
 * the refusal usually also contains the words for what was attempted.
 */
const DISCLAIMED = /(擋下|被擋|拒絕|未能|沒有成功|失敗|無法|not allowed|refused|blocked|could not|failed|denied)/i;

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

export class BlockedClaimTracker {
  private refused = new Set<string>();
  private landed = new Set<string>();

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
    if (!CLAIM.test(text)) return null;
    if (DISCLAIMED.test(text)) return null;

    const stillRefused = [...this.refused].filter((t) => !this.landed.has(t));
    const named = stillRefused.filter((t) => text.includes(t) || text.includes(leaf(t)));
    if (!named.length) return null;

    return {
      message:
        `[SYSTEM] 上一輪對 ${named.map(leaf).join("、")} 的變更**被守衛擋下,並未發生**,` +
        `但你的回覆說它完成了。請先確認檔案的實際內容,再據實更正給使用者 —— ` +
        `守衛擋下的東西如果被回報成已完成,擋下來就失去意義了。` +
        `擋阻理由裡有下一步該怎麼做。`,
    };
  }

  /** One turn's history. */
  reset(): void {
    this.refused.clear();
    this.landed.clear();
  }
}
