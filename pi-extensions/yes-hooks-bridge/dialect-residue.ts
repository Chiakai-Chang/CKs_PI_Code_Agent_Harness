/**
 * Residue from a tool-call dialect the model was taught but Pi does not use.
 *
 * Measured on session 019ffbdd (2026-08-13, 6.5 hours, model
 * Muse-Glimmer-30B-Abliterated-Q6_K): the served chat template renders tool
 * calls as
 *
 *     <atem:function_calls>
 *     <atem:invoke name="write">
 *     <atem:parameter name="content">…</atem:parameter>
 *     </atem:invoke>
 *     </atem:function_calls>
 *
 * and its tool-definition block teaches the model to emit exactly that, while
 * Pi drives the model with native OpenAI `tool_calls`. The model closed its last
 * argument the way its template taught it, and the closing tag — decoded
 * mangled as `</atem:日>` — landed INSIDE the argument value. 24 times in that
 * one session:
 *
 *   - in `content`, so 20 files in a real project still end in it
 *   - once in `path`: `…/.gitignore</atem:日>` -> ENOENT on `mkdir '…\.gitignore<'`
 *
 * Nothing in this harness saw it. `FAKE_TOOL_CALL_PATTERN` matched `<invoke`
 * and `<parameter name=`, and `<atem:invoke` does not match `<invoke\b` — one
 * namespace prefix walked a whole dialect past every detector in the repo.
 *
 * WHO THIS SPEAKS TO. Not the model. The model cannot change its own chat
 * template; telling it about the residue costs a turn and, on the evidence of
 * the GateGuard misdelivery in the same session, can change what it does next
 * for the worse. The argument is repaired in place — `tool_call` handlers may
 * mutate `event.input`, per the contract in the installed
 * `core/extensions/types.d.ts`:
 *
 *     /** Block tool execution. To modify arguments, mutate `event.input` in
 *         place instead. *\/
 *
 * — and the OPERATOR is told, through `ctx.ui.notify` and a report file that
 * outlives the session. The real fix is a server restart, which is theirs to
 * make; `scripts/check-model-serving.py` names it.
 *
 * WHY IT IS NOT SILENT. A filter that quietly deletes the symptom leaves the
 * cause running and teaches nobody. This repo has that scar: the citation gate
 * moved URLs-in-files from 0 to 10 and fabricated ones from 0 to 4 in the same
 * run, because a threshold defines the shape of the evasion. So every removal
 * is counted, named, and written down.
 */

/** Local names that only a tool-call dialect uses. Prefixed or bare. */
const DIALECT_NAMES = [
  "parameter", "invoke", "function_calls", "function_call",
  "tool_call", "tool_code", "tools", "function", "antml", "atem",
];

const NAMED_TAG = new RegExp(
  String.raw`<\/(?:[A-Za-z][\w.-]*:)?(?:${DIALECT_NAMES.join("|")})\s*>`, "i");

/**
 * A namespaced closing tag whose local part is not a valid ASCII XML name —
 * `</atem:日>` is the measured case, a closing tag whose local part decoded to a
 * single CJK character.
 *
 * Split from NAMED_TAG deliberately. A mangled tag cannot be recognised by its
 * name, only by its shape, and a rule broad enough to catch it would eat honest
 * markup: `</xsl:template>` and `</svg:path>` are ordinary content in a file
 * this agent might legitimately write. Requiring the local part to be
 * un-name-like keeps those out — an NCName is exactly what they have.
 */
const MANGLED_NAMESPACED_TAG = /<\/[A-Za-z][\w.-]*:[^<>\s]{0,24}>/;

// End-anchored. Trailing only: a dialect tag in the middle of a file is content
// the model meant to write — documentation about tool calls, a captured
// template, this very comment. Only the one the decoder appended sits at the
// end. Anchoring rather than comparing indices matters for the stacked case:
// `</atem:parameter></atem:invoke></atem:function_calls>` closes three levels,
// and an unanchored match finds the FIRST tag, which is not at the end, so the
// whole value was left untouched.
const NAMED_TAG_AT_END = new RegExp(NAMED_TAG.source + "$", "i");
const MANGLED_TAG_AT_END = new RegExp(MANGLED_NAMESPACED_TAG.source + "$");

function trailingTagAt(value: string): { tag: string } | null {
  const trimmed = value.replace(/\s+$/, "");
  for (const re of [NAMED_TAG_AT_END, MANGLED_TAG_AT_END]) {
    const m = trimmed.match(re);
    if (!m) continue;
    if (re === MANGLED_TAG_AT_END) {
      const local = m[0].slice(m[0].indexOf(":") + 1, -1);
      // A well-formed local name is somebody's markup, not our residue.
      if (/^[A-Za-z_][\w.-]*$/.test(local)) continue;
    }
    return { tag: m[0] };
  }
  return null;
}

/** Strip every dialect closing tag stacked at the end of one value. */
export function stripTrailingDialectTags(value: string): { value: string; removed: string[] } {
  if (typeof value !== "string" || !value) return { value, removed: [] };
  let out = value;
  const removed: string[] = [];
  // `</atem:parameter></atem:invoke></atem:function_calls>` closes three levels
  // in one breath, so one pass is not enough.
  for (let i = 0; i < 8; i++) {
    const hit = trailingTagAt(out);
    if (!hit) break;
    removed.push(hit.tag);
    out = out.slice(0, out.replace(/\s+$/, "").length - hit.tag.length);
  }
  if (!removed.length) return { value, removed };
  return { value: out, removed };
}

export interface ResidueRemoval {
  tool: string;
  field: string;
  tag: string;
}

/**
 * Repair one tool call's arguments in place. Returns what was removed, so the
 * caller can tell the operator; an empty array means the call was untouched.
 *
 * Field names come from the installed schemas (`core/tools/{write,edit,bash}.d.ts`),
 * not from memory: write is {path, content}, edit is {path, edits[].oldText,
 * edits[].newText}, bash is {command}. A guess here would repair a field that
 * does not exist and leave the one that does.
 */
export function scrubToolInput(toolName: string, input: unknown): ResidueRemoval[] {
  if (!input || typeof input !== "object") return [];
  const rec = input as Record<string, unknown>;
  const out: ResidueRemoval[] = [];

  const scrub = (holder: Record<string, unknown>, field: string) => {
    const cur = holder[field];
    if (typeof cur !== "string") return;
    const { value, removed } = stripTrailingDialectTags(cur);
    if (!removed.length) return;
    holder[field] = value;
    for (const tag of removed) out.push({ tool: toolName, field, tag });
  };

  if (toolName === "write") {
    scrub(rec, "path");
    scrub(rec, "content");
  } else if (toolName === "edit") {
    scrub(rec, "path");
    const edits = rec.edits;
    if (Array.isArray(edits)) {
      for (const e of edits) {
        if (e && typeof e === "object") {
          scrub(e as Record<string, unknown>, "oldText");
          scrub(e as Record<string, unknown>, "newText");
        }
      }
    }
  }
  // Deliberately NOT bash.command, and not query/pattern/url.
  //
  // runawayArgumentGuard already blocks any call whose serialized input contains
  // tool-call syntax, and its complaint is the better one for those fields: "you
  // started a call and kept generating instead of stopping at its end" is a
  // model behaviour the model can fix. Template residue is not — the model
  // cannot change its own chat template — which is why write/edit are repaired
  // here instead of refused.
  //
  // The two are distinguishable and this is the line between them: residue is
  // exactly ONE trailing closing tag on an argument whose value is an artifact
  // going to disk. A leak in a `query` is short, has no artifact, and is
  // overwhelmingly the runaway case; `tests/test_universal_tool_parser.py`
  // states that decision outright ("Size is not the tell — tool-call markup
  // inside a value always is"), and reversing it silently for every field would
  // be the undocumented reversal this repo has been bitten by.
  //
  // If bash commands are later observed carrying residue, widen it here with the
  // session that showed it — not before.
  return out;
}
