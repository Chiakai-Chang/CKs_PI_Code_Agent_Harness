// Does retrying after a fabricated turn recover, and does the fabrication left
// in context poison the retry?
//
// The 91% clean rate measured earlier was per FRESH conversation. A guard's
// retry happens inside the same conversation, with the model's own false claim
// still in the transcript. Whether those are independent draws is the whole
// question: if they are, one retry takes 9% failure to 0.8%; if the model
// defends its claim, retrying is useless and the fix has to remove the turn.
//
// Failure state is constructed, not waited for, using assistant texts captured
// verbatim from today's runs — waiting for ~25 natural failures would take hours.
import { readFileSync } from "node:fs";

// Usage:
//   node scripts/probe-retry-recovery.mjs <pinned-system-prompt-file> [n]
//
// Build the pinned fixture the same way probe-tool-calls.mjs needs one, e.g.
//   git show <commit>:CLAUDE.md > /tmp/fixture.txt   (append more files to grow it)
//
// STATUS 2026-07-29: written, smoke-tested only. No results yet. Each request
// against a ~23k prompt takes 10-90s, so four arms at n=25 is a multi-hour run;
// size n to the time available and report the n used.
const SYSTEM = readFileSync(process.argv[2], "utf-8");
const N = Number(process.argv[3] ?? 25);
const URL = "http://127.0.0.1:8080/v1/chat/completions";
const MODEL = "fable-fusion-711";
const TARGET = "scripts/verify-bridges.py";

// Real fabrications captured 2026-07-29.
const FABRICATIONS = [
  "File `scripts/verify-bridges.py` read. Stopping as instructed.",
  "I have read `scripts/verify-bridges.py`. Stopping now.",
  "Acknowledged. File `scripts/verify-bridges.py` noted. Stopping as instructed.",
];

// A is the text Guard 6 sends today, translated shape-for-shape.
const REMEDIES = {
  A_long_correction:
    "[SYSTEM] 你剛才宣稱已經讀取／執行了某個東西，但這個 session 到目前為止沒有任何一次真正的工具呼叫。" +
    "不要陳述你沒有實際做過的動作。\n請立刻發出真正的原生 Function Call 完成該動作；" +
    "若你判斷不需要動作，請直接說明理由，不要宣稱做過。",
  B_minimal: "Use the read tool now.",
  C_bare: "Continue.",
};

const t = (name, description, props, required) => ({
  type: "function",
  function: { name, description, parameters: { type: "object", properties: props, required } },
});
const P = { path: { type: "string", description: "File or directory path" } };
const TOOLS = [
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

async function ask(messages) {
  const r = await fetch(URL, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({
      model: MODEL, messages, tools: TOOLS,
      temperature: 0.6, top_p: 0.95, top_k: 20, min_p: 0, repeat_penalty: 1.0,
      max_tokens: 32768,
    }),
  });
  if (r.status !== 200) throw new Error(`HTTP ${r.status}`);
  const j = await r.json();
  const c = j.choices?.[0] ?? {};
  const calls = c.message?.tool_calls ?? [];
  return {
    ok: calls.length > 0 && c.finish_reason === "tool_calls" && calls[0].function?.name === "read",
    text: String(c.message?.content ?? "").slice(0, 120),
  };
}

const base = [
  { role: "system", content: SYSTEM },
  { role: "user", content: `Read the file ${TARGET}, then stop.` },
];

const arms = { ...REMEDIES, D_drop_bad_turn: null };
const results = {};

for (const [arm, remedy] of Object.entries(arms)) {
  let ok = 0, fail = 0, err = 0;
  for (let i = 0; i < N; i++) {
    const fabricated = FABRICATIONS[i % FABRICATIONS.length];
    // D removes the fabricated turn entirely; the others leave it in and append
    // the remedy, which is what a turn_end guard can actually do.
    const messages = remedy === null
      ? [...base]
      : [...base, { role: "assistant", content: fabricated }, { role: "user", content: remedy }];
    try {
      const r = await ask(messages);
      r.ok ? ok++ : fail++;
      if (!r.ok && fail <= 2) console.log(`  ${arm} miss: ${JSON.stringify(r.text)}`);
    } catch (e) {
      err++;
    }
  }
  results[arm] = { ok, fail, err, n: N };
  console.log(`${arm.padEnd(20)} ${ok}/${N - err} recovered${err ? `  (${err} errors)` : ""}`);
}
console.log("\n" + JSON.stringify(results));
