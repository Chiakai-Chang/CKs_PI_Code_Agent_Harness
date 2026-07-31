/**
 * Deep Research Bridge
 *
 * Turns `deep-research-guide` from advice into a mechanism.
 *
 * The skill described decomposition, subagent fan-out and cited synthesis, but
 * nothing implemented any of it — the model was asked to imagine having
 * subagents. This registers a real `deep_research` tool that spawns each
 * sub-question as its own `pi --print` process (Pi's own documented subagent
 * pattern, examples/extensions/subagent) and returns only a compact digest.
 *
 * Shaped by two measurements on this machine, not by preference:
 *
 *   1. llama.cpp runs with `-np 1`, so concurrent requests SERIALIZE — two
 *      parallel requests finished at 7.3s and 14.3s. Fanning out in parallel
 *      buys nothing and multiplies wall time, so sub-questions run one at a
 *      time and the cap is deliberately low.
 *   2. Large tool results derail this model: a 42,999-char result was observed
 *      losing the conversation mid-task. So the value here is NOT parallelism —
 *      it is context isolation. Each child burns its own context reading pages;
 *      the parent receives a bounded digest and never sees the pages at all.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { spawn } from "node:child_process";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, basename } from "node:path";
import {
  CHILD_MARKER,
  MAX_SUB_QUESTIONS,
  buildDigest,
  childPrompt,
  childSystemPrompt,
  clampFinding,
  parseChildOutput,
  summarizeChildStderr,
  validateSubQuestions,
  type SubResult,
} from "./research.js";

// Generous: one child does several web fetches on a slow local model. The cap
// exists to stop a hung child holding the parent forever, not to rush research.
const CHILD_TIMEOUT_MS = 15 * 60 * 1000;

function toolError(text: string) {
  return { content: [{ type: "text" as const, text }], isError: true };
}

/** Locate the pi executable the same way Pi's own subagent example does. */
function piInvocation(args: string[]): { command: string; args: string[] } {
  const script = process.argv[1];
  const execName = basename(process.execPath).toLowerCase();
  const isGenericRuntime = /^(node|bun)(\.exe)?$/.test(execName);
  if (script && !script.startsWith("/$bunfs/root/") && isGenericRuntime) {
    return { command: process.execPath, args: [script, ...args] };
  }
  if (!isGenericRuntime) return { command: process.execPath, args };
  return { command: "pi", args };
}

function runChild(
  subQuestion: string,
  question: string,
  cwd: string,
): Promise<{ text: string; ok: boolean; seconds: number }> {
  const started = Date.now();
  return new Promise((resolve) => {
    let dir: string | null = null;
    let promptFile: string;
    try {
      dir = mkdtempSync(join(tmpdir(), "pi-deepresearch-"));
      promptFile = join(dir, "system.txt");
      writeFileSync(promptFile, childSystemPrompt(question), { encoding: "utf-8", mode: 0o600 });
    } catch (e) {
      return resolve({ text: `could not stage the child prompt: ${String(e)}`, ok: false, seconds: 0 });
    }

    const inv = piInvocation([
      "--print",
      "--mode", "json",
      "--no-session",
      // A child stands in the PARENT'S cwd — the repo — and until 2026-07-30 it
      // also held the full built-in tool set. A pure research question ("what
      // is llama.cpp's Qwen3.5 MTP support?") ended with a child editing
      // scripts/make-probe-fixture.py and dropping a stray file in the repo
      // root. Neither write appears in the parent's session log, because
      // `--no-session` means children leave no audit trail by construction: the
      // parent had made exactly one tool call, `deep_research`, and the damage
      // was found only by an incidental `git status`.
      //
      // Recursion was already anticipated (CHILD_MARKER below); mutation was
      // not. A research child has no business changing this machine.
      //
      // Denylist, not a `--tools` allowlist: the harm is exactly "mutates the
      // local machine", which is these three names. An allowlist would have to
      // enumerate every research tool and would silently reduce a child to
      // nothing the moment one name drifts — and returning nothing is an
      // already-observed failure mode of this bridge.
      "--exclude-tools", "bash,edit,write",
      "--append-system-prompt", promptFile,
      childPrompt(subQuestion),
    ]);

    const proc = spawn(inv.command, inv.args, {
      cwd,
      shell: false,
      stdio: ["ignore", "pipe", "pipe"],
      timeout: CHILD_TIMEOUT_MS,
      // The marker is what makes recursion impossible: a child that somehow
      // reaches for deep_research finds the tool refusing. Without it, one
      // confused decomposition could fork agents until the machine dies.
      env: { ...process.env, [CHILD_MARKER]: "1" },
    });

    let out = "";
    let err = "";
    proc.stdout.on("data", (d: Buffer) => (out += d.toString()));
    proc.stderr.on("data", (d: Buffer) => (err += d.toString()));

    const finish = (ok: boolean, fallback: string) => {
      if (dir) { try { rmSync(dir, { recursive: true, force: true }); } catch {} }
      const seconds = (Date.now() - started) / 1000;
      const text = parseChildOutput(out);
      resolve(text ? { text, ok: true, seconds } : { text: fallback, ok, seconds });
    };

    proc.on("error", (e) => finish(false, `could not start a child agent: ${e.message}`));
    proc.on("exit", (code) =>
      finish(code === 0, `child agent exited ${code} with no answer. ${summarizeChildStderr(err)}`.trim()),
    );
  });
}

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "deep_research",
    label: "Deep Research",
    description:
      "Research a question by running each sub-question as its OWN agent process, then return a compact digest. "
      + "Each sub-question gets a fresh context that reads the web on its own; only the findings come back here, "
      + "so pages you never want in this conversation stay out of it. Decompose the question yourself first and "
      + `pass 2-${MAX_SUB_QUESTIONS} concrete sub-questions. They run one at a time and each costs a full agent `
      + "turn, so choose the few that actually change the answer.",
    promptSnippet:
      "deep_research(question, subQuestions[]): fan out sub-questions to isolated agent processes, get findings back",
    promptGuidelines: [
      "deep_research is a TOOL, not a skill — call it directly. Do not look it up in the skill catalog.",
      "Use deep_research when a question needs several distinct things looked up and you do not want the raw pages in this context.",
      "Decompose first: pass sub-questions that are separately answerable, not restatements of each other.",
      "For a single lookup, call web_search/web_open directly — deep_research costs one agent run per sub-question.",
    ],
    parameters: Type.Object({
      question: Type.String({ description: "The overall research question, in one sentence" }),
      subQuestions: Type.Array(Type.String(), {
        description: `2-${MAX_SUB_QUESTIONS} concrete, separately answerable sub-questions`,
      }),
    }),
    async execute(_id, params: any, _signal, onUpdate: any, ctx: any) {
      if (process.env[CHILD_MARKER]) {
        return toolError(
          "deep_research is not available inside a research subagent. Answer your own sub-question "
          + "with web_search / web_open and report the finding.",
        );
      }
      const validated = validateSubQuestions(params?.subQuestions);
      if (!validated.ok) return toolError(validated.error);
      const question = String(params?.question ?? "").trim();
      if (!question) return toolError("question is required — one sentence describing what is being researched.");

      const cwd = typeof ctx?.cwd === "string" && ctx.cwd ? ctx.cwd : process.cwd();
      const results: SubResult[] = [];

      for (let i = 0; i < validated.questions.length; i++) {
        const sub = validated.questions[i];
        // Sequential on purpose (see the -np 1 measurement in the header).
        // onUpdate is the only sign of life during what can be many minutes.
        onUpdate?.({
          content: [{
            type: "text" as const,
            text: `[deep_research] ${i + 1}/${validated.questions.length}: ${sub}`,
          }],
        });
        const r = await runChild(sub, question, cwd);
        results.push({ question: sub, finding: clampFinding(r.text), ok: r.ok, seconds: r.seconds });
      }

      const failed = results.filter((r) => !r.ok).length;
      if (failed === results.length) {
        return toolError(
          `Every sub-question failed. First error: ${results[0]?.finding ?? "unknown"}. `
          + "Do not invent findings — tell the user research could not run.",
        );
      }
      return {
        content: [{ type: "text" as const, text: buildDigest(question, results) }],
        details: {
          subQuestions: results.length,
          failed,
          seconds: Math.round(results.reduce((a, r) => a + r.seconds, 0)),
        },
      };
    },
  });

  pi.registerCommand?.("deep-research", {
    description: "Research a question via isolated subagent processes and write a cited answer",
    handler: async (args: string, cmdCtx: any) => {
      const question = String(args ?? "").trim();
      if (!question) {
        cmdCtx?.ui?.notify?.('Usage: /deep-research <question>', "warning");
        return;
      }
      pi.sendMessage?.(
        {
          customType: "deep-research",
          content:
            `Research this question: ${question}\n\n`
            + `Decompose it into 2-${MAX_SUB_QUESTIONS} concrete sub-questions, call the deep_research tool once `
            + `with them, then synthesize the returned findings into a cited answer. Keep the source URLs.`,
          display: true,
        },
        // "followUp" so the run actually starts. `triggerTurn` is ignored for
        // "nextTurn" (Pi docs), which would leave /deep-research queueing a
        // prompt that does nothing until the user types again.
        { deliverAs: "followUp", triggerTurn: true },
      );
    },
  });
}
