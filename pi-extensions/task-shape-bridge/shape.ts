/**
 * Is this request multi-step, and is the model about to skip straight past it?
 *
 * Measured before writing this (scripts/measure-triggers.py, local model,
 * isolated sessions, neutral cwd, repeats=3):
 *
 *   debug-methodology         2/3   67%
 *   multi-step-methodology    0/3    0%
 *
 * All 21 methodology skills are in the system prompt with their descriptions —
 * confirmed by dumping it, 39,980 chars. Debugging fires because the request
 * lands in systematic-debugging's vocabulary. A market survey lands in nobody's:
 * those descriptions are written for software work ("creating features, building
 * components") and they live in submodules this repo does not edit.
 *
 * So the routing happens here instead, and it must be cheap — this runs at the
 * top of every turn, before the model is called, so it may not call one itself.
 */

/** Verbs that open work with more than one answer in it. */
const RESEARCH_VERBS = [
  "research", "survey", "investigate", "compare", "analyse", "analyze",
  "audit", "evaluate", "assess", "benchmark", "review the landscape",
  "調查", "研究", "分析", "比較", "盤點", "評估", "市場調查", "可行性",
];

/**
 * Words that separate one deliverable from the next.
 *
 * The optional trailing conjunction is what makes "X, Y, and Z" three things
 * rather than four: without it the Oxford comma and the `and` after it are two
 * separate matches, and every list came out one item too long.
 *
 * The FULLWIDTH COMMA was missing until 2026-08-09, and it is the separator
 * Chinese actually uses. The prompt that exposed it — session 019fe60f, sixteen
 * turns of real research — contains five of them, zero ASCII commas and zero
 * ideographic commas, so it counted 2 deliverables and classified as
 * single-step. This classifier was very nearly blind to the language its owner
 * writes in.
 */
const CONJUNCTIONS =
  /(?:,|，|、|;|；)\s*(?:and\b|plus\b|as well as\b|以及|還有)?|\band\b|\bplus\b|\bas well as\b|以及|還有|跟|與/gi;

/** Phrases that say "there is more than one of these" outright. */
const EXPLICIT_MULTI = [
  /\ball three\b/i, /\ball four\b/i, /\bboth\b/i,
  /\beach of\b/i, /\bone by one\b/i, /三者|三項|多個|各項|逐一/,
];

/**
 * Tools whose first use commits to an approach.
 *
 * Reading one file is how a careful agent starts and must not be treated as
 * skipping the plan. Opening a search is the move this exists to interrupt.
 */
const BROAD_TOOLS = new Set(["web_search", "deep_research", "bash"]);

export function isBroadTool(toolName: string): boolean {
  return BROAD_TOOLS.has(String(toolName || "").toLowerCase());
}

export interface RequestShape {
  multiStep: boolean;
  deliverables: number;
  reason: string;
}

/**
 * Classify a request by shape.
 *
 * Deliberately conservative. Misjudging a single lookup as multi-step turns
 * "never fires" into "fires on everything", and a line the model sees on every
 * turn is a line it learns to skip — which is exactly how the previous delivery
 * failed in the other direction.
 *
 * Length alone decides nothing: one thing said slowly is still one thing.
 */
/**
 * Length in Latin-equivalent characters.
 *
 * The floor below exists to stop a greeting being routed, and it was calibrated
 * on English. A CJK character carries roughly twice the content of a Latin one,
 * so "研究並比較三個競品的定價與功能差異,並整理成表格" — research, compare,
 * three competitors, pricing, features, and a table — is 24 characters and was
 * discarded before any signal was looked at.
 *
 * Measured 2026-08-10 over real session history: 62 opening prompts contain CJK
 * and 6 of them (10%) fall under the raw floor. The bias is silent, because the
 * function returns the same shape as a genuine single-step request.
 *
 * Found by adding this module's sibling to the mutation sweep, which is the
 * finding T1 was for: 33 of 48 pure modules had never been swept, and coverage
 * of the sweep — not the wording of assertions — is what surfaces this class.
 */
export function weightedLength(text: string): number {
  let n = 0;
  for (const ch of text) {
    // CJK ideographs, plus the kana and Hangul blocks that behave the same way.
    n += /[぀-ヿ㐀-䶿一-鿿가-힯豈-﫿]/.test(ch)
      ? 2 : 1;
  }
  return n;
}

export function classifyRequest(prompt: string | null | undefined): RequestShape {
  const text = String(prompt || "").trim();
  if (weightedLength(text) < 25) {
    return { multiStep: false, deliverables: 0, reason: "" };
  }

  const lower = text.toLowerCase();
  const hasResearchVerb = RESEARCH_VERBS.some(v => lower.includes(v.toLowerCase()));
  const explicitlyPlural = EXPLICIT_MULTI.some(re => re.test(text));

  // Count separators only inside the sentence that carries the ask. Counting
  // them across a whole paragraph makes any politely-worded single request look
  // like a list.
  const deliverables = countDeliverables(text);

  // `deliverables >= 4` used to be sufficient on its own. Adding the fullwidth
  // comma to the separator set made that shortcut wrong: English commas often
  // separate deliverables, Chinese ones mostly separate clauses inside a single
  // sentence, so counting alone promoted
  // "我想洗車，洗車店離我家只有50公尺，你覺得我該走過去，還是開車去？" to multi-step.
  // Measured over 106 real prompts from this machine: keeping the shortcut gave
  // 35% multi-step and caught the car-wash question; removing it gives 17% and
  // still catches session 019fe60f, the request this work started from.
  if (deliverables >= 3 && (hasResearchVerb || explicitlyPlural)) {
    return {
      multiStep: true,
      deliverables,
      reason: `${deliverables} separate deliverables in one request`,
    };
  }

  if (hasResearchVerb && explicitlyPlural) {
    return {
      multiStep: true,
      deliverables: Math.max(deliverables, 2),
      reason: "a research request that names more than one thing to cover",
    };
  }

  return { multiStep: false, deliverables, reason: "" };
}

/**
 * The script handed to the model when it reaches for a broad tool.
 *
 * Routine (arXiv 2507.14447) raised multi-step tool-calling accuracy on
 * Qwen3-14B from 32.6% to 83.3%, and its mechanism is giving the model a
 * structured script rather than asking it to choose from a list. This harness
 * already hands it a 122-entry catalogue at session start and measured 0/3 on
 * exactly this request shape. So: name the two skills, say what was counted, and
 * leave a way out.
 *
 * The way out is not politeness. Under `pi --print` there is nobody to approve a
 * hard stop, and a router that cannot be overruled by a model that is right
 * becomes something to route around.
 */
export function buildRoutine(shape: RequestShape): string {
  if (!shape.multiStep) return "";
  return (
    `This request looks like ${shape.deliverables} separate deliverables. ` +
    `Before searching, take one of two paths:\n` +
    `  A. Scope is clear -> load the \`planning-with-files\` skill (it is registered; ` +
    `use it by name, do not go looking for the file), write task_plan.md with one ` +
    `phase per deliverable, then do one phase at a time and verify each before ` +
    `starting the next.\n` +
    `  B. Scope is not clear -> load the \`brainstorming\` skill and settle the open ` +
    `questions first.\n` +
    `If this really is a single lookup, say so in one sentence and carry on.`
  );
}

/**
 * The same routine, at the other end of the context.
 *
 * The first design delivered only on the tool result, and it was measured
 * failing: the routine arrived in the first web_search's result and the model
 * ignored it across 17 tool calls. `ToolCallEventResult` is `{block, reason}`,
 * so a tool_call handler cannot add text without blocking — delivering at
 * tool_result means delivering *after* the search ran, with the model committed
 * and results already in hand.
 *
 * Two findings shape this. Models attend most to the beginning and the end of a
 * context and drift in the middle; and an instruction that matters should appear
 * in several places at once rather than one. So the routine goes into the system
 * prompt before the turn as well, and stays on the tool result for recency.
 *
 * Shorter than the tool-result version: this one is paid for on every turn of a
 * multi-step task, not once.
 */
export function buildSystemPromptNote(
  shape: RequestShape,
  options?: { interactive?: boolean },
): string {
  if (!shape.multiStep) return "";
  const interactive = options?.interactive !== false;

  // One run in five asked four scoping questions — geography, time window,
  // product definition, output format — and stopped. Interactively that is the
  // better move before a market survey. Under `pi --print` there is nobody to
  // answer, and the run ended with no work and no artifacts.
  //
  // The model cannot tell which mode it is in. `ExtensionContext.hasUI` can, so
  // the harness says it rather than asking the model to guess.
  const scope = interactive
    ? "Use `brainstorming` first if the scope is unclear."
    : "Nobody can answer questions in this run: write your assumptions into the plan and proceed rather than stopping to ask.";

  return (
    `[task-shape] This request looks like ${shape.deliverables} separate deliverables. ` +
    `Plan before executing: load the \`planning-with-files\` skill and write task_plan.md ` +
    `with one phase per deliverable, then work one phase at a time. ${scope} ` +
    `If it really is a single lookup, say so and carry on.`
  );
}

/**
 * How many things is this asking for?
 *
 * Separators are counted per sentence and the largest run wins: a request is
 * multi-part because one sentence lists several things, not because a paragraph
 * happens to contain several commas.
 */
function countDeliverables(text: string): number {
  let best = 0;
  for (const sentence of text.split(/[.!?。！？\n]/)) {
    const s = sentence.trim();
    if (s.length < 12) continue;
    const separators = (s.match(CONJUNCTIONS) || []).length;
    if (separators > 0) best = Math.max(best, separators + 1);
  }
  return best;
}
