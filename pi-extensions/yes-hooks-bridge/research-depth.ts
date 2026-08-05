/**
 * The run that searches wide, reads nothing, and leaves nothing behind.
 *
 * Measured 2026-08-05, Pi session 019fd29d-4e18-7970-835b-87b2d2ae46cc — a real
 * research request, three turns, run to completion:
 *
 *     40 tool calls = 38 web_search + 2 web_open + 0 write/edit
 *     distinct query signatures: 40      max repeat: 1
 *
 * `loop-detect.ts` was correct to stay silent: no query was ever repeated. This
 * is a third shape, and neither existing guard can see it. The consecutive guard
 * watches for AAAA. The cycle guard watches for ABCABCABC. This one is
 * ABCDEFGHIJ… — forty distinct questions, none of them followed anywhere.
 *
 * Two things went wrong, and they are separate:
 *
 *   Depth. Two pages opened out of thirty-eight searches. Every conclusion in
 *   that session rests on search-result snippets, which are written to earn a
 *   click rather than to be quoted. The tell was in the output itself: the same
 *   person is referred to as 他 in one paragraph and 她 in another, which is what
 *   stitching snippets together without reading them looks like.
 *
 *   Residue. Nothing was written. Afterwards the working directory held `.git`
 *   and nothing else. The investigation existed only in context — not
 *   reviewable, not resumable, and no claim traceable to its source. The harness
 *   owner's point, and the reason C.A.S.E. exists: work that lives only in
 *   context gets the model's natural pull toward closing the topic, while work
 *   split across files gets a fresh context per piece.
 *
 * Refusing a search is the only lever that reaches either one. There is no
 * "about to answer" event, and advice loses to momentum — the task-shape router
 * delivered a correct routing note attached to the FIRST search of that very
 * session, and thirty-seven searches followed it.
 *
 * So: block, but only past the point where the next search could still be the
 * useful one, and never in a way that can trap the run. This repo's scar from
 * GateGuard is a gate nobody had ever run denying the first bash command of
 * every session; the retirement rule below exists because of it.
 */

/** Searches allowed before anything at all has been read in full. */
export const OPEN_AFTER_SEARCHES = 8;

/** Searches allowed before anything at all has been written down. */
export const WRITE_AFTER_SEARCHES = 12;

/**
 * How many times one gate may refuse before it gives up for the session.
 *
 * `web_open` can fail for reasons the run does not control — the site refuses
 * the fetch, the address 404s, the page is a login wall. A gate that demands
 * something impossible and never relents turns a shallow run into a stuck one,
 * which is worse. Three refusals is enough to change a mind that can be changed.
 */
export const MAX_BLOCKS_PER_GATE = 3;

/**
 * How long a written file has to be before it is expected to say where its
 * content came from.
 *
 * A plan, a progress note or a one-line status has nothing to cite. The three
 * measured reports were 3,482 / 3,788 / 4,295 chars, so this sits well below
 * them and well above the notes.
 */
export const CITE_MIN_CHARS = 800;

/** Pages that must have been read before a file is expected to cite any. */
export const CITE_MIN_OPENS = 2;

/**
 * Unsourced characters allowed across the whole session, however they are split.
 *
 * The per-call floor above is satisfied by writing smaller. Measured the day
 * this gate shipped: one run refused at a 4,524-char report and then wrote
 * 773 + 475 + 143 + 109 + 626 in pieces, finishing with 6,657 chars on disk and
 * not one address. Nothing about the artifact changed; only the chunk size did.
 */
export const CITE_MAX_UNSOURCED_TOTAL = 2500;

/** Tools that count as having read something in full. */
const READ_TOOLS = new Set(["web_open"]);

/** Tools that count as having written something down. */
const WRITE_TOOLS = new Set(["write", "edit"]);

const HAS_URL = /https?:\/\//i;

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

export interface DepthBlock {
  block: true;
  reason: string;
}

type GateName = "depth" | "artifact" | "citation";

/** How many addresses to quote back. Enough to act on, short enough to read. */
const REASON_URLS = 6;

export class ResearchDepthGuard {
  private searches = 0;
  private opens = 0;
  private writes = 0;
  private readUrls: string[] = [];
  private unsourcedChars = 0;
  private sourcedSomething = false;
  private blocked = new Map<GateName, number>();
  private retired = new Set<GateName>();

  /**
   * Counts the call, and refuses it if it is a search that has run past one of
   * the two gates.
   *
   * Counting happens on the ATTEMPT, not the result — this guard sees
   * `tool_call`, which fires before the tool runs, and there is no honest way to
   * know from here whether the page loaded. That is deliberate rather than a
   * compromise: a `web_open` that fails still clears the depth gate, so a run
   * that genuinely cannot read a page is never held against a wall.
   */
  check(toolName: string, input?: unknown): DepthBlock | null {
    const name = String(toolName || "").toLowerCase();

    if (READ_TOOLS.has(name)) {
      this.opens++;
      const url = (input as Record<string, unknown> | undefined)?.url;
      if (typeof url === "string" && url) this.readUrls.push(url);
      return null;
    }
    if (WRITE_TOOLS.has(name)) {
      // Counted before the citation check can refuse it. A refusal here means
      // "write this again with its sources", not "you have written nothing" —
      // if the artifact gate could still see zero writes it would start
      // refusing searches over a file this guard itself sent back.
      this.writes++;
      return this.citationCheck(input);
    }
    if (name !== "web_search") return null;

    this.searches++;

    if (this.searches > OPEN_AFTER_SEARCHES && this.opens === 0) {
      const hit = this.refuse("depth");
      if (hit) {
        return {
          block: true,
          reason:
            `Depth guard: ${this.searches} searches, 0 pages opened. Every answer ` +
            `built from here rests on result snippets, which are written to earn ` +
            `a click, not to be quoted. Call \`web_open\` on one of the addresses ` +
            `the results already gave you. Reading one page beats a ninth query.`,
        };
      }
    }

    if (this.searches > WRITE_AFTER_SEARCHES && this.writes === 0) {
      const hit = this.refuse("artifact");
      if (hit) {
        return {
          block: true,
          reason:
            `Artifact guard: ${this.searches} searches and nothing written to ` +
            `disk. When this session ends, none of it can be reviewed, resumed, ` +
            `or traced back to a source. Write what you have so far to a file ` +
            `(findings.md, or a phase file if a plan exists) — one line per claim ` +
            `with the URL it came from — then carry on searching.`,
        };
      }
    }

    return null;
  }

  /**
   * Refuses a substantial file that names no source, after pages were read.
   *
   * Measured across three runs of the market-survey scenario with the other two
   * gates installed: 11, 6 and 9 pages opened; reports of 3,788 / 4,295 / 3,482
   * chars written; zero URLs in any file. The addresses that did appear were in
   * the chat reply only, and one of those was invented — a shopee.tw search
   * endpoint assembled from a pattern rather than read.
   *
   * All three runs had read `research-task-routing`, whose findings table
   * carries a mandatory `Source` column. The instruction was already rewritten
   * once, from a sentence into a table column with a blank cell, precisely
   * because it was being ignored. It was ignored again, three times out of
   * three. Text inside a skill loses; this is the channel that does not.
   *
   * The reason quotes the addresses back, because the failure is not refusal to
   * cite — it is that by the time the report is written, the URLs are far back
   * in the context and the page content is not.
   */
  private citationCheck(input: unknown): DepthBlock | null {
    if (this.opens < CITE_MIN_OPENS) return null;
    let text: string;
    try {
      text = outgoingText(input);
    } catch {
      return null;
    }
    if (HAS_URL.test(text)) {
      // One sourced file settles the session. The cumulative rule exists to
      // catch a report broken into pieces, not to nag a run that has already
      // shown its work and is now writing ordinary short notes.
      this.sourcedSomething = true;
      return null;
    }
    if (this.sourcedSomething) return null;

    this.unsourcedChars += text.length;
    const oversize = text.length >= CITE_MIN_CHARS;
    const accumulated = this.unsourcedChars >= CITE_MAX_UNSOURCED_TOTAL;
    if (!oversize && !accumulated) return null;
    if (!this.refuse("citation")) return null;

    const list = this.readUrls.slice(-REASON_URLS).map((u) => `  ${u}`).join("\n");
    const scale = oversize
      ? `this file is ${text.length} chars`
      : `${this.unsourcedChars} chars have been written this session`;
    return {
      block: true,
      reason:
        `Citation guard: ${scale} and not one address appears in any of them, ` +
        `after ${this.opens} page(s) were read. A report nobody can trace is the ` +
        `polished version of a report nobody can check. Write it again with the ` +
        `source next to each claim, and cite ONLY pages this session actually ` +
        `opened — if there are fewer sources than claims, say which claims are ` +
        `unsourced rather than inventing an address for them. The pages opened ` +
        `so far:\n${list}`,
    };
  }

  /**
   * Records a refusal and reports whether it should actually be delivered.
   *
   * Returns false once the gate has spent its budget, and retires it: a rule the
   * run has declined three times is not going to work on the fourth, and the
   * only thing further refusals can still do is deadlock the session.
   */
  private refuse(gate: GateName): boolean {
    if (this.retired.has(gate)) return false;
    const count = (this.blocked.get(gate) ?? 0) + 1;
    this.blocked.set(gate, count);
    if (count > MAX_BLOCKS_PER_GATE) {
      this.retired.add(gate);
      return false;
    }
    return true;
  }

  /** A new session starts with no history. */
  reset(): void {
    this.searches = 0;
    this.opens = 0;
    this.writes = 0;
    this.readUrls = [];
    this.unsourcedChars = 0;
    this.sourcedSomething = false;
    this.blocked.clear();
    this.retired.clear();
  }

  /** For the TUI line and for measurement. */
  stats(): { searches: number; opens: number; writes: number } {
    return { searches: this.searches, opens: this.opens, writes: this.writes };
  }
}
