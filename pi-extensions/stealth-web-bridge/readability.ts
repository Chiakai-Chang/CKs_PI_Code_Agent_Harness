/**
 * Reading view for accessibility-tree snapshots.
 *
 * The idea is borrowed from pi-browser-harness (research/pi-browser-harness,
 * src/domains/readpage/readability.ts) — strip navigation, chrome and link
 * plumbing so what reaches the model is the page's actual content. The method
 * is deliberately NOT borrowed: that implementation captures raw DOM blocks via
 * CDP and *guesses* which are article body by scoring text density against link
 * density. We are handed an accessibility tree, where every node already
 * carries its semantic role, so filtering by role is both simpler and more
 * reliable than a density heuristic — and it needs no in-page script injection,
 * no extra round trip, and cannot break on a hostile page.
 *
 * Measured on real snapshots (see tests/fixtures):
 *
 *   Wikipedia article, 8,253 chars    /url plumbing 43.1%, prose 22.9%
 *   News homepage,    34,375 chars    link lines 34.2%, prose 31.7%
 *
 * and of 57 `[eN]` element refs on the Wikipedia page, ZERO sat on a prose
 * line. Dropping the interactive scaffolding therefore costs no content, and
 * conversely a reading view can drop refs wholesale without losing anything a
 * reader needs.
 *
 * Link TITLES are kept while their `/url:` lines are dropped: on an index or
 * search-results page the headlines *are* links, and prose-only filtering would
 * return a page with its headlines removed. Measured: prose-only keeps 31.5% of
 * a news homepage, prose+link-titles 63.5% — the extra 32% is the headlines.
 */

/** Lines whose role carries readable content. */
const PROSE = /-\s+(paragraph|text|heading|blockquote|listitem|code|article|main|caption|term|definition|cell|rowheader|columnheader)\b/;

/** `- link "Some title" [e3]:` — the title is content, the URL underneath is not. */
const LINK = /-\s+link\b/;

/** `- /url: https://...` — pure plumbing for a reader. */
const URL_LINE = /^\s*-\s*\/url:/;

/** Interactive and decorative scaffolding: useful for clicking, noise for reading. */
const CHROME =
  /-\s+(navigation|banner|contentinfo|menu|menuitem|menubar|searchbox|button|combobox|option|img|image|separator|tablist|tab|form|textbox|checkbox|radio|slider|status|complementary|toolbar|progressbar|switch|spinbutton)\b/;

/**
 * Container roles whose entire SUBTREE is boilerplate.
 *
 * This is the one idea worth taking wholesale from pi-browser-harness's
 * readability: its `inBoilerplate` flag, set when an ancestor is nav/header/
 * footer/aside. Line-by-line filtering is not enough — dropping a `navigation`
 * line while keeping its child links leaves exactly the junk the reading view
 * exists to remove. First run against the real Wikipedia fixture returned
 * "Donate", "Create account", "Log in", "Article", "Talk" as content.
 *
 * The AX snapshot is indented, so a subtree is "every following line indented
 * deeper than its root".
 */
const BOILERPLATE_CONTAINER =
  /-\s+(navigation|banner|contentinfo|complementary|menu|menubar|toolbar|search|form|tablist|dialog|alertdialog)\b/;

function indentOf(line: string): number {
  const m = line.match(/^(\s*)/);
  return m ? m[1].length : 0;
}

const REF = /\s*\[e\d+\]/g;

export interface ReadableResult {
  text: string;
  keptLines: number;
  totalLines: number;
  originalChars: number;
  readableChars: number;
}

/**
 * Reduce an AX-tree snapshot to its readable content.
 *
 * Fails open: if filtering would leave almost nothing (an app shell, a page
 * that is genuinely all widgets), the original snapshot is returned unchanged.
 * Returning an empty "article" would look like a successfully read blank page,
 * which is the failure mode that had web_snapshot handing back "(empty
 * snapshot)" as a success for six turns in a row.
 */
export function extractReadable(snapshot: string, minChars = 200): ReadableResult {
  const lines = snapshot.split("\n");
  const kept: string[] = [];
  // Indent of the boilerplate container currently being skipped, or null.
  let skipDeeperThan: number | null = null;

  for (const line of lines) {
    const indent = indentOf(line);
    if (skipDeeperThan !== null) {
      if (line.trim() !== "" && indent <= skipDeeperThan) skipDeeperThan = null;
      else continue;
    }
    if (BOILERPLATE_CONTAINER.test(line)) {
      skipDeeperThan = indent;
      continue;
    }
    if (URL_LINE.test(line)) continue;
    const isProse = PROSE.test(line);
    if (!isProse && CHROME.test(line)) continue;
    if (!isProse && !LINK.test(line)) continue;
    const cleaned = line.replace(REF, "").trimEnd();
    // A role label with nothing after it carries no information once its
    // children have been filtered away.
    if (!/[A-Za-z0-9一-鿿]/.test(cleaned.replace(/^\s*-\s*\w+:?\s*$/, ""))) {
      if (/^\s*-\s*\w+:?\s*$/.test(cleaned)) continue;
    }
    kept.push(cleaned);
  }

  const text = kept.join("\n").replace(/\n{3,}/g, "\n\n").trim();
  const result: ReadableResult = {
    text,
    keptLines: kept.length,
    totalLines: lines.length,
    originalChars: snapshot.length,
    readableChars: text.length,
  };

  if (text.length < minChars && snapshot.length >= minChars) {
    return { ...result, text: snapshot, readableChars: snapshot.length, keptLines: lines.length };
  }
  return result;
}

/**
 * The reading view handed to the model, with the note that makes interaction
 * still reachable. web_click / web_type need `[eN]` refs, which this view
 * removes on purpose — so it has to say where they are. (Historically those
 * tools have never been called: 223 web tool calls on this machine, 0 of them
 * interaction. The refs are overhead for every observed use, but the capability
 * stays one tool call away rather than being removed.)
 */
export function formatReadingView(header: string, r: ReadableResult): string {
  if (r.text === "" ) return header;
  const trimmed = r.readableChars < r.originalChars;
  const footer = trimmed
    ? `\n\n[reading view: ${r.keptLines}/${r.totalLines} lines, ${r.readableChars}/${r.originalChars} chars. `
      + `Navigation, URLs and element refs removed. Call web_snapshot on this tab for the full tree with [eN] refs if you need to click or type.]`
    : "";
  return `${header}\n\n${r.text}${footer}`;
}
