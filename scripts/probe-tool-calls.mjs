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
//
// The target file must NOT appear in the system prompt: asking for something the
// model already has makes "I already have it" a correct answer with no tool
// call, which reads as a failure and is not one.

import { readFileSync } from "node:fs";

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
const temp = Number(arg("temp", "0.6"));
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
const FABRICATION = /(?:I(?:'ve| have)\s+(?:already\s+)?read|(?:File|The file)\s+[`"'][^`"']+[`"']\s+(?:has been\s+)?read\b|已(?:經)?讀取)/i;

const system = readFileSync(systemFile, "utf-8");
const results = [];

for (let i = 1; i <= repeats; i++) {
  const started = Date.now();
  let json, status = 0;
  try {
    const r = await fetch(`${url}/v1/chat/completions`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        model,
        messages: [
          { role: "system", content: system },
          { role: "user", content: `Read the file ${target}, then stop.` },
        ],
        tools,
        temperature: temp,
        max_tokens: 32768,
      }),
    });
    status = r.status;
    // llama-server answers /props while still loading but 503s here. Treating
    // that as "no tool call" invalidated a whole batch once.
    if (status !== 200) throw new Error(`HTTP ${status}`);
    json = await r.json();
  } catch (e) {
    results.push({ run: i, error: String(e.message || e) });
    if (!asJson) console.log(`run ${i}: REQUEST FAILED ${e.message || e}`);
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
  process.stdout.write(JSON.stringify({ model, tools: tools.length, temp, systemFile, clean: cleanCount, total: results.length, results }, null, 2));
} else {
  const shapes = {};
  for (const r of results) shapes[r.shape ?? "request-failed"] = (shapes[r.shape ?? "request-failed"] ?? 0) + 1;
  console.log(`\nclean ${cleanCount}/${results.length}  tools=${tools.length} temp=${temp} model=${model}`);
  console.log("shapes: " + Object.entries(shapes).map(([k, v]) => `${k}=${v}`).join(", "));
}
process.exit(cleanCount === results.length ? 0 : 1);
