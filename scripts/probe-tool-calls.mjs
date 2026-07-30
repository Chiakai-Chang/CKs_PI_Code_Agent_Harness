#!/usr/bin/env node
// Measures whether a local model actually emits native tool calls under load.
//
// Why this exists: the dominant failure at this harness's prompt scale is not
// markup and not a runaway argument — it is a turn that ends cleanly having
// done nothing (`finish_reason=stop`, zero tool calls) while claiming the work
// was done or denying the capability. Nothing in the harness can see that from
// the inside, so it has to be measured against the engine directly.
//
// Measured 2026-07-29 (grm-2.6-plus, both quants, 13 tools):
//   light  (~500 prompt tokens)     -> 3/3 clean
//   heavy  (~23,000 prompt tokens)  -> 0/6 clean
//
// The system prompt MUST be a pinned file. An earlier version assembled it from
// the repo's live docs; writing up the results changed those docs, which changed
// the prompt, which changed the measurement. Pin it:
//
//   git show HEAD:docs/KNOWN_ISSUES.md > /tmp/fixture.md   # or any fixed text
//
// Usage:
//   node scripts/probe-tool-calls.mjs --system <file> [--repeats 6]
//        [--url http://127.0.0.1:8080] [--model grm-2.6-plus] [--temp 0.6]
//        [--target scripts/verify-bridges.py] [--tools 13] [--json]
//        [--max-tokens 32768] [--no-cache-prompt]
//
// Every run lands in exactly one bucket. `timeout` and `truncated` are
// failures, not lost data: a turn that never answered and a turn that never
// stopped are both turns that did not call the tool.
//
// The target file must NOT appear in the system prompt: asking for something the
// model already has makes "I already have it" a correct answer with no tool
// call, which reads as a failure and is not one.

import { readFileSync } from "node:fs";
import http from "node:http";
import https from "node:https";

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}
const has = (name) => process.argv.includes(`--${name}`);

const systemFile = arg("system", null);
if (!systemFile) {
  console.error("--system <file> is required (a PINNED system prompt file; see header)");
  process.exit(2);
}
const url = arg("url", "http://127.0.0.1:8080").replace(/\/$/, "");
const model = arg("model", "grm-2.6-plus");
const repeats = Number(arg("repeats", "6"));
// Every sampler is pinned in the request, not left to the server's defaults.
// Comparing two models means comparing two launch scripts, and theirs differ
// (grm: min_p 0.05 / repeat-penalty 1.05; fable-fusion: min_p 0.0 / 1.0) — that
// is a second variable in what is supposed to be a single-variable comparison.
// Defaults below are the intersection of both model cards' "thinking mode,
// precise coding" preset, and honour Fable-Fusion's MTP rule (temp <= 1,
// repeat-penalty off).
const temp = Number(arg("temp", "0.6"));
const topK = Number(arg("top-k", "20"));
const topP = Number(arg("top-p", "0.95"));
const minP = Number(arg("min-p", "0"));
const repPen = Number(arg("rep-pen", "1.0"));
// llama.cpp reuses the slot's KV prefix across requests. Every repeat after the
// first therefore runs against a different engine state than the first, and
// state left by whatever ran before the batch carries in too. Measured
// 2026-07-29: the same server, prompt and samplers gave 0/6 in the morning and
// 5/6 ten hours later, so something time- or state-dependent dominates a
// six-run batch. --no-cache-prompt forces a full reprocess per request, which
// costs ~90s each here but removes cross-request state as an explanation.
const noCachePrompt = has("no-cache-prompt");
// Kept at the original 32768 so existing baselines stay comparable, but made a
// flag because a model whose end-of-generation tokens are broken will run to
// this limit on EVERY turn that does not produce a tool call. Laguna-S-2.1's
// GGUF ships that defect ("special_eos_id is not in special_eog_ids"), which at
// ~22 t/s costs 25 minutes per failed run — long enough that a batch cannot be
// finished at all. Lower it to bound the failure, and read the resulting
// `truncated` shape as "never stopped", not as "declined".
const maxTokens = Number(arg("max-tokens", "32768"));
const target = arg("target", "scripts/verify-bridges.py");
const toolCount = Number(arg("tools", "13"));
const asJson = has("json");

const t = (name, description, props, required) => ({
  type: "function",
  function: { name, description, parameters: { type: "object", properties: props, required } },
});
const P = { path: { type: "string", description: "File or directory path" } };
const ALL_TOOLS = [
  t("read", "Read a file from disk. Use for source files, docs and configuration.", P, ["path"]),
  t("write", "Write a file to disk, creating or overwriting it.", { ...P, content: { type: "string" } }, ["path", "content"]),
  t("edit", "Replace an exact string inside an existing file.", { ...P, old_string: { type: "string" }, new_string: { type: "string" } }, ["path", "old_string", "new_string"]),
  t("bash", "Run a shell command in the project directory.", { command: { type: "string" } }, ["command"]),
  t("ls", "List the entries of a directory.", P, ["path"]),
  t("grep", "Search file contents with a regular expression.", { pattern: { type: "string" }, ...P }, ["pattern"]),
  t("find", "Find files by glob pattern.", { pattern: { type: "string" }, ...P }, ["pattern"]),
  t("web_search", "Search the live web and return result snippets.", { query: { type: "string" } }, ["query"]),
  t("web_open", "Open a URL and return its readable text.", { url: { type: "string" } }, ["url"]),
  t("deep_research", "Run a multi-step research task over the web.", { query: { type: "string" } }, ["query"]),
  t("skill", "Load a named skill's instructions into context.", { name: { type: "string" } }, ["name"]),
  t("todo", "Record or update the task list for this session.", { items: { type: "string" } }, ["items"]),
  t("compact", "Summarise and compact the conversation context.", { instructions: { type: "string" } }, []),
];
const tools = ALL_TOOLS.slice(0, Math.max(1, Math.min(toolCount, ALL_TOOLS.length)));

// Tool-call markup leaking into the message text or into an argument value.
const LEAK = /<tool_call>|<function\s*=|<parameter|<invoke\b|```(?:bash|json)/i;
// The two shapes that pass for a normal turn while doing nothing.
const DENIAL = /(?:do(?:n['’]?t| not)|cannot|can['’]?t|no)\s+(?:have\s+)?(?:direct(?:ly)?\s+|live\s+)?access/i;
// Kept in step with FABRICATED_COMPLETION in yes-hooks-bridge/index.ts — if the
// probe and the guard disagree about what counts as a fabricated completion, the
// probe's shape counts stop describing what the harness will actually catch. The
// bare-claim branch comes from a live capture at a 41,129-token prompt whose
// whole answer was `File read. Stopping as instructed.`
const FABRICATION = /(?:I(?:'ve| have)\s+(?:already\s+)?read|(?:File|The file)\s+[`"'][^`"']+[`"']\s+(?:has been\s+)?read\b|已(?:經)?讀取|(?:^|[.!?]\s+|\n)\s*(?:The\s+)?(?:file|files|contents?|directory|dir)\s+read\s*(?=[.,;!]|$))/i;

// A turn that spends minutes generating prose is a FAILED turn, not a broken
// measurement. Recording it as an `error` drops it out of the clean/total ratio
// entirely, so the runs most likely to be failures are the ones that silently
// disappear and the reported rate is biased clean. probe-retry-recovery.mjs was
// fixed for this on 2026-07-29; this script was not, and on 2026-07-29 a
// 15,280-token batch against Laguna-S-2.1 hit it on the first request.
const TIMEOUT_MS = Number(process.env.PROBE_TIMEOUT_MS ?? 240000);

// Why node:http and not fetch. llama.cpp answers a NON-STREAMING request only
// when generation has finished, so the socket is silent for the whole run and
// the response headers arrive last. undici enforces its own ~300s
// `headersTimeout`, which `AbortSignal.timeout` does not override and Node
// exposes no way to raise. Measured 2026-07-30 at a 41,129-token prompt (~249s
// of prefill alone): runs 1, 3 and 5 died as `fetch failed` while the server
// completed them anyway, and runs 2, 4 and 6 then hit the warm KV prefix and
// returned in ~70s. Reported as 2/6 clean, the batch was really 3 usable runs —
// a silent 50% data loss that also inverted the timings. node:http's
// `setTimeout` is an idle-socket deadline, which for this traffic pattern is
// exactly the whole-request deadline we want, and PROBE_TIMEOUT_MS becomes the
// only limit in play.
const postJson = (endpoint, bodyObj) =>
  new Promise((resolve, reject) => {
    const u = new URL(endpoint);
    const mod = u.protocol === "https:" ? https : http;
    const payload = Buffer.from(JSON.stringify(bodyObj));
    const req = mod.request(
      {
        hostname: u.hostname,
        port: u.port || (u.protocol === "https:" ? 443 : 80),
        path: u.pathname + u.search,
        method: "POST",
        headers: { "content-type": "application/json", "content-length": payload.length },
      },
      (res) => {
        const chunks = [];
        res.on("data", (c) => chunks.push(c));
        res.on("end", () => resolve({ status: res.statusCode, text: Buffer.concat(chunks).toString("utf8") }));
        res.on("error", reject);
      },
    );
    req.setTimeout(TIMEOUT_MS, () => {
      const err = new Error(`no answer within ${TIMEOUT_MS}ms`);
      err.name = "TimeoutError";
      req.destroy(err);
    });
    req.on("error", reject);
    req.end(payload);
  });

const system = readFileSync(systemFile, "utf-8");
const results = [];

for (let i = 1; i <= repeats; i++) {
  const started = Date.now();
  let json, status = 0;
  try {
    const r = await postJson(`${url}/v1/chat/completions`, {
      model,
      messages: [
        { role: "system", content: system },
        { role: "user", content: `Read the file ${target}, then stop.` },
      ],
      tools,
      temperature: temp,
      top_p: topP,
      top_k: topK,
      min_p: minP,
      repeat_penalty: repPen,
      ...(noCachePrompt ? { cache_prompt: false } : {}),
      max_tokens: maxTokens,
    });
    status = r.status;
    // llama-server answers /props while still loading but 503s here. Treating
    // that as "no tool call" invalidated a whole batch once.
    if (status !== 200) throw new Error(`HTTP ${status}`);
    json = JSON.parse(r.text);
  } catch (e) {
    const secs = ((Date.now() - started) / 1000).toFixed(1);
    // A timeout is a result; anything else (connection refused, 503 while the
    // model is still loading, malformed JSON) is a broken instrument and stays
    // an error so it cannot be mistaken for a model failure.
    const timedOut = e?.name === "TimeoutError" || /timeout|aborted/i.test(String(e?.message ?? ""));
    if (timedOut) {
      results.push({
        run: i, clean: false, shape: "timeout",
        finish: null, calls: 0, name: null, argsLen: 0,
        promptTokens: null, outputTokens: null, seconds: Number(secs),
        head: `(no answer within ${TIMEOUT_MS}ms)`,
      });
      if (!asJson) console.log(`run ${i}: DIRTY shape=timeout after ${secs}s (limit ${TIMEOUT_MS}ms)`);
    } else {
      results.push({ run: i, error: String(e.message || e) });
      if (!asJson) console.log(`run ${i}: REQUEST FAILED ${e.message || e}`);
    }
    continue;
  }

  const secs = ((Date.now() - started) / 1000).toFixed(1);
  const choice = json.choices?.[0] ?? {};
  const msg = choice.message ?? {};
  const calls = msg.tool_calls ?? [];
  const content = String(msg.content ?? "");
  const args = String(calls[0]?.function?.arguments ?? "");
  const leaked = LEAK.test(content) || LEAK.test(args);
  const clean = calls.length > 0 && !leaked && choice.finish_reason === "tool_calls";
  const shape = clean ? "clean"
    : leaked ? "markup-leak"
    : DENIAL.test(content) ? "capability-denial"
    : FABRICATION.test(content) ? "fabricated-completion"
    : calls.length > 0 ? "wrong-call"
    // Ran out of max_tokens without ever calling anything. Folding this into
    // no-call hides the difference between "declined to act" and "generated
    // until it was cut off", which are different problems with different fixes
    // (Laguna-S-2.1 interleaves unbounded native thinking, so it can do this).
    : choice.finish_reason === "length" ? "truncated"
    : "no-call";

  results.push({
    run: i, clean, shape,
    finish: choice.finish_reason, calls: calls.length,
    name: calls[0]?.function?.name ?? null, argsLen: args.length,
    promptTokens: json.usage?.prompt_tokens ?? null,
    outputTokens: json.usage?.completion_tokens ?? null,
    seconds: Number(secs),
    head: clean ? null : content.slice(0, 160),
  });
  if (!asJson) {
    console.log(
      `run ${i}: ${clean ? "CLEAN" : "DIRTY"} shape=${shape} finish=${choice.finish_reason}` +
      ` calls=${calls.length} name=${calls[0]?.function?.name ?? "-"} args_len=${args.length}` +
      ` prompt_tok=${json.usage?.prompt_tokens} out_tok=${json.usage?.completion_tokens} ${secs}s`);
    if (!clean) console.log(`   head: ${JSON.stringify(content.slice(0, 160))}`);
  }
}

const cleanCount = results.filter((r) => r.clean).length;
if (asJson) {
  process.stdout.write(JSON.stringify({ model, tools: tools.length, samplers: { temp, topK, topP, minP, repPen }, systemFile, clean: cleanCount, total: results.length, results }, null, 2));
} else {
  const shapes = {};
  for (const r of results) shapes[r.shape ?? "request-failed"] = (shapes[r.shape ?? "request-failed"] ?? 0) + 1;
  console.log(`\nclean ${cleanCount}/${results.length}  model=${model} tools=${tools.length}` +
    ` temp=${temp} top_k=${topK} top_p=${topP} min_p=${minP} rep_pen=${repPen}`);
  console.log("shapes: " + Object.entries(shapes).map(([k, v]) => `${k}=${v}`).join(", "));
}
process.exit(cleanCount === results.length ? 0 : 1);
