/**
 * Pure helpers for deep-research fan-out. Kept out of index.ts so a test can
 * execute them: index.ts imports `typebox`, which bare node cannot resolve.
 */

export const MAX_SUB_QUESTIONS = 5;
export const MAX_FINDING_CHARS = 6000;

/** Guard env var: set in every child so a subagent can never re-enter the tool. */
export const CHILD_MARKER = "PI_HARNESS_DEEP_RESEARCH_CHILD";

export function validateSubQuestions(input: unknown): { ok: true; questions: string[] } | { ok: false; error: string } {
  if (!Array.isArray(input)) return { ok: false, error: "subQuestions must be an array of strings." };
  const questions = input.filter((q): q is string => typeof q === "string" && q.trim().length > 0).map((q) => q.trim());
  if (questions.length === 0) {
    return { ok: false, error: "subQuestions is empty. Decompose the question into 2-5 concrete sub-questions first." };
  }
  if (questions.length > MAX_SUB_QUESTIONS) {
    // A hard cap, not a suggestion. Each sub-question is a full agent run, and
    // with llama.cpp `-np 1` those run strictly one after another (measured:
    // two concurrent requests finished at 7.3s and 14.3s, i.e. serialized).
    // Ten sub-questions is not a thorough report, it is an hour of wall time.
    return {
      ok: false,
      error: `${questions.length} sub-questions exceeds the cap of ${MAX_SUB_QUESTIONS}. `
        + `Sub-questions run sequentially, so each one costs a full agent turn of wall time. `
        + `Pick the ${MAX_SUB_QUESTIONS} that most change the answer.`,
    };
  }
  return { ok: true, questions };
}

/** The system prompt appended to each child agent. */
export function childSystemPrompt(question: string): string {
  return [
    "You are a research subagent. You have ONE sub-question to answer, and your entire output",
    "is fed back to a parent agent that never sees the pages you read.",
    "",
    `Parent's overall question: ${question}`,
    "",
    "Rules:",
    "- Use web_search to find sources, then web_open to READ the most relevant 1-3 of them.",
    "  Titles and snippets alone are not evidence.",
    "- Report only what the sources actually say. If they do not answer the sub-question, say so.",
    "- Every claim must carry its source URL inline.",
    "- Be compact. The parent needs findings, not transcripts. Aim for well under 400 words.",
    "- End with nothing but the finding. No preamble, no offer to continue.",
  ].join("\n");
}

export function childPrompt(subQuestion: string): string {
  return `Sub-question: ${subQuestion}\n\nResearch it against the live web and report your finding with source URLs.`;
}

/** Trim one child's answer to a budget, marking that it was cut. */
export function clampFinding(text: string, max = MAX_FINDING_CHARS): string {
  const t = text.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max)}\n\n[finding truncated at ${max} chars]`;
}

export interface SubResult {
  question: string;
  finding: string;
  ok: boolean;
  seconds: number;
}

/**
 * Assemble the digest handed back to the parent.
 *
 * This is the whole point of the mechanism: the children burn their own context
 * reading pages, and the parent receives only this. Keeping the digest small is
 * what makes sequential fan-out worth its wall-clock cost on a local model.
 */
export function buildDigest(question: string, results: SubResult[]): string {
  const ok = results.filter((r) => r.ok).length;
  const lines = [
    `[deep_research] ${ok}/${results.length} sub-questions answered for: ${question}`,
    `Each ran as a separate agent process, so none of the page content below entered this context.`,
    "",
  ];
  for (const r of results) {
    lines.push(`## ${r.question}`);
    lines.push(r.ok ? r.finding : `(failed after ${r.seconds.toFixed(0)}s — ${r.finding})`);
    lines.push("");
  }
  lines.push("---");
  lines.push(
    "Synthesize these findings into the answer. Keep the source URLs. "
    + "Where findings disagree, say so rather than averaging them. "
    + "If a sub-question failed, state that it is unresolved instead of filling the gap from memory.",
  );
  return lines.join("\n");
}

/** Extract the child's final assistant text from `pi --print --mode json` output. */
export function parseChildOutput(stdout: string): string {
  const texts: string[] = [];
  for (const line of stdout.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed.startsWith("{")) continue;
    let event: any;
    try {
      event = JSON.parse(trimmed);
    } catch {
      continue;
    }
    const msg = event?.message;
    if (event?.type === "message_end" && msg?.role === "assistant") {
      const content = msg.content;
      if (typeof content === "string") texts.push(content);
      else if (Array.isArray(content)) {
        for (const c of content) {
          if (c && c.type === "text" && typeof c.text === "string") texts.push(c.text);
        }
      }
    }
  }
  // Only the last assistant message is the finding; earlier ones are the
  // child's own tool-use narration, which the parent must not inherit.
  return texts.length > 0 ? texts[texts.length - 1].trim() : "";
}

/**
 * Turn a failed child's stderr into something that says WHY it failed.
 *
 * Was `err.slice(-300)`. A child's stderr ends with whatever the bridges
 * printed on their way up, so on 2026-07-30 three of four failed sub-questions
 * reported nothing but `[ecc-bridge] ECC Submodule Version: 2.0.0` — the tail is
 * exactly the wrong end to keep, because banners come last and causes come
 * first.
 *
 * Bridge banners are the one shape we can drop with confidence: they are
 * `[name] ...` lines emitted at startup by extensions in this repo. Anything
 * else is kept, oldest first, so the first real error survives later noise.
 */
export function summarizeChildStderr(stderr: string, max = 300): string {
  const lines = String(stderr ?? "")
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .filter((l) => !/^\[[a-z0-9][a-z0-9-]*\]/i.test(l));
  if (lines.length === 0) return "(no error output — the child produced nothing on stderr)";
  const joined = lines.join(" | ");
  return joined.length <= max ? joined : joined.slice(0, max) + "…";
}
