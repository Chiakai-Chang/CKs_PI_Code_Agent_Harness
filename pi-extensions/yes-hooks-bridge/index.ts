/**
 * Safety Hooks Bridge Extension (folder: yes-hooks-bridge)
 *
 * Hosts deterministic guards the model CANNOT ignore — the whole point of a
 * hook over a text rule, and especially valuable with weak/uncensored local
 * models that drift past AGENTS.md prose under load:
 *
 *   1. Destructive-command guard — wires YES.md's `pre-bash-guard.sh` to block
 *      `rm -rf /`, `git push --force`, `DROP TABLE`, `mkfs`, fork bombs, … on the
 *      `bash` tool. Scope deliberately narrow (MECE): only the destructive
 *      blocker; YES.md's post-edit / post-deploy reminders duplicate AGENTS.md §9
 *      and are intentionally skipped. The behavioral-discipline half of YES.md
 *      ships as the `yes` skill, not here.
 *
 *   2. Directory-containment guard — blocks `write`/`edit` whose resolved target
 *      escapes the session cwd (the project root Pi was launched in). Fixes the
 *      observed "資料夾亂跳" failure: a run in one project wrote files into a
 *      sibling project AND edited this harness's own scripts. Relative paths
 *      resolve under cwd (allowed); absolute or `../` paths that leave cwd are
 *      blocked. Fails open if cwd/path can't be resolved.
 *
 *   3. Loop guard — on `turn_end`, catches a turn that made no real tool call
 *      but whose text is shaped like one (`<invoke>`, `<read-files>`, `<bash>
 *      <command>`, …). These never execute; a weak model can echo the shape
 *      from Pi's own compaction-summary format (which legitimately ends with
 *      `<read-files>`/`<modified-files>` tags) and then loop on its own echo.
 *      After 3 consecutive strikes, queues a corrective message for the next
 *      turn — AGENTS.md §4's "3-Strike Cap", enforced as code.
 */
import type { ExtensionAPI, ToolCallEvent, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { readFileSync, existsSync } from "node:fs";
import { dirname, join, resolve, relative, isAbsolute } from "node:path";
import { fileURLToPath } from "node:url";
import { homedir } from "node:os";
import { spawnSync } from "node:child_process";

function harnessRoot(): string {
  const here = dirname(fileURLToPath(import.meta.url));
  try {
    const pkg = JSON.parse(readFileSync(join(here, "package.json"), "utf-8"));
    if (pkg["pi-harness"]?.root) return pkg["pi-harness"].root;
  } catch {}
  return join(here, "../..");
}

function guardScript(): string {
  return join(harnessRoot(), "external/yes.md/hooks/pre-bash-guard.sh");
}

// Resolve a real shell (Node's bare "sh" ENOENTs on Windows — see stealth-web).
function findShell(): string {
  try {
    const cfg = JSON.parse(readFileSync(join(homedir(), ".pi", "agent", "settings.json"), "utf-8"));
    if (cfg.shellPath && existsSync(cfg.shellPath)) return cfg.shellPath;
  } catch {}
  for (const c of [
    "C:\\Program Files\\Git\\bin\\bash.exe",
    "C:\\Program Files\\Git\\usr\\bin\\bash.exe",
    "C:\\Program Files (x86)\\Git\\bin\\bash.exe",
  ]) {
    try { if (existsSync(c)) return c; } catch {}
  }
  return process.platform === "win32" ? "bash" : "sh";
}

// Guard 1: destructive shell commands, via YES.md pre-bash-guard.sh.
function bashGuard(event: ToolCallEvent, ctx: ExtensionContext) {
  const cmd = (event.input as { command?: unknown })?.command;
  if (typeof cmd !== "string" || !cmd) return;
  const script = guardScript();
  if (!existsSync(script)) return; // yes.md submodule absent — fail open, don't break bash
  let r;
  try {
    r = spawnSync(findShell(), [script, cmd], { timeout: 4000, encoding: "utf-8" });
  } catch {
    return; // guard itself failed — fail open rather than block legit work
  }
  if (r.status === 1) {
    const matched = (r.stdout || "")
      .split("\n")
      .map((l) => l.trim())
      .find((l) => l.startsWith("Matched:")) || "destructive pattern";
    ctx.ui.notify(`🚨 YES.md blocked a destructive command (${matched})`, "error");
    return {
      block: true,
      reason: `YES.md pre-bash-guard blocked a destructive command (${matched}). If you truly need it, ask the user to run it.`,
    };
  }
}

// Guard 2: keep write/edit inside the session cwd (the project Pi was launched in).
// Mirrors Pi's own resolveToCwd: relative paths resolve under cwd; absolute paths
// stay absolute. A target that escapes cwd (sibling project, this harness, home) is
// blocked so a drifting model can't scatter files across the disk.
// Guard 2b: writes into a vendored git submodule.
//
// Observed for real: asked to load a skill, the model took the path out of
// skill-catalog.json and, instead of reading it, `write`-d its own invented
// content over external/ecc/skills/agent-architecture-audit/SKILL.md —
// destroying the genuine upstream skill. The containment guard let it through
// because external/ is inside the project root, which is exactly right for
// containment and exactly wrong here: submodule contents are vendored, they
// belong to another repository, and an edit there is silently lost on the next
// `git submodule update` even when it is not a hallucination.
//
// Reads are untouched. `bash` is not covered — a human deliberately
// contributing upstream still can, via git — so this blocks the accident
// without blocking the intent.
function submoduleRoots(cwd: string): string[] {
  try {
    const gitmodules = readFileSync(join(cwd, ".gitmodules"), "utf-8");
    return [...gitmodules.matchAll(/^\s*path\s*=\s*(.+?)\s*$/gm)].map((m) => m[1].replace(/\\/g, "/"));
  } catch {
    return [];
  }
}

function vendoredGuard(
  event: ToolCallEvent,
  ctx: ExtensionContext,
  cwd: string,
  target: string,
  rel: string,
) {
  const relPosix = rel.replace(/\\/g, "/");
  const hit = submoduleRoots(cwd).find((p) => relPosix === p || relPosix.startsWith(p + "/"));
  if (!hit) return;
  ctx.ui.notify(`🚨 Blocked ${event.toolName} into vendored submodule ${hit}: ${target}`, "error");
  return {
    block: true,
    reason:
      `Vendored submodule: "${target}" lives inside the git submodule "${hit}", which is another ` +
      `repository's content. Writing there overwrites upstream files and is discarded by the next ` +
      `submodule update. If you meant to READ this file (e.g. to load a skill), use the read tool. ` +
      `If you genuinely need to change upstream code, tell the user rather than editing in place.`,
  };
}

// Guard 4: a native tool call whose ARGUMENTS ran away.
//
// Observed on this machine, and the most damaging failure found all day. The
// model opened a real `web_search` call and then, inside the `query` string,
// began emitting XML-format tool calls and looping on them:
//
//   {"query": "Wikipedia \"Accessibility tree\"</parameter>\n</function>\n
//    </tool_call>\n<tool_call>\n<function>web_search>\n<parameter=query>\n…"}
//
// 145,638 characters of that, until the 32,768-token output cap was hit
// (usage.output = 32768, stopReason = "length"). Pi then refuses the call —
// "the response hit the output token limit, so its arguments may be truncated"
// — and the model simply tries again the same way. Two attempts, ~700 seconds,
// a 297KB session, zero progress.
//
// None of the other guards see this: it IS a native tool call, so the loop
// guard's "no real tool call" test never fires, and the garbage lives inside
// the arguments, which FAKE_TOOL_CALL_PATTERN (a message-text scan) never
// inspects.
//
// Blocking costs nothing — Pi was going to reject the call anyway — but it
// replaces a confusing engine message with a specific instruction, which is the
// difference between the model repeating the failure and correcting it.
const ARG_SYNTAX_LEAK = /<\/?(?:tool_call|function|parameter)\b|<\|tool▁call/i;
const MAX_ARG_CHARS = 8000;

function runawayArgumentGuard(event: ToolCallEvent, ctx: ExtensionContext) {
  let serialized: string;
  try {
    serialized = JSON.stringify(event.input ?? {});
  } catch {
    return; // unserializable input — not our business, fail open
  }
  const leaked = ARG_SYNTAX_LEAK.test(serialized);
  const oversized = serialized.length > MAX_ARG_CHARS;
  if (!leaked && !oversized) return;

  // An oversized `content`/`command` is legitimate — writing a big file, running
  // a long script. Only the syntax leak is unambiguous on its own; size alone
  // is judged on fields that should never be large.
  if (!leaked) {
    const input = (event.input ?? {}) as Record<string, unknown>;
    const bulkFields = ["content", "command", "newText", "text"];
    const nonBulk = Object.entries(input)
      .filter(([k]) => !bulkFields.includes(k))
      .reduce((n, [, v]) => n + (typeof v === "string" ? v.length : 0), 0);
    if (nonBulk <= MAX_ARG_CHARS) return;
  }

  ctx.ui.notify(
    `🚨 ${event.toolName} arguments ran away (${serialized.length} chars${leaked ? ", tool-call syntax leaked into a value" : ""})`,
    "error",
  );
  return {
    block: true,
    reason:
      `Your ${event.toolName} arguments are malformed: ${serialized.length} characters` +
      (leaked ? `, and a value contains raw tool-call syntax (</parameter>, </tool_call>, <function>).` : ".") +
      ` You started a tool call and then kept generating instead of stopping at its end. ` +
      `Emit ONE call with short, plain arguments — for a search, the query is a few words — and ` +
      `stop generating immediately after it. Do not put tool-call markup inside an argument value.`,
  };
}

function containmentGuard(event: ToolCallEvent, ctx: ExtensionContext) {
  const input = event.input as { path?: unknown; file_path?: unknown };
  const raw = typeof input?.path === "string" ? input.path
    : typeof input?.file_path === "string" ? input.file_path : "";
  if (!raw || typeof ctx.cwd !== "string" || !ctx.cwd) return; // can't decide — fail open
  let cwd: string, target: string;
  try {
    cwd = resolve(ctx.cwd);
    target = resolve(cwd, raw); // raw absolute -> unchanged; raw relative -> under cwd
  } catch {
    return; // path math failed — fail open rather than block legit work
  }
  const rel = relative(cwd, target);
  const inside = rel === "" || (!rel.startsWith("..") && !isAbsolute(rel));
  if (inside) return vendoredGuard(event, ctx, cwd, target, rel);
  ctx.ui.notify(`🚨 Blocked ${event.toolName} outside project root: ${target}`, "error");
  return {
    block: true,
    reason: `Directory containment: ${event.toolName} target "${target}" is outside the project root (${cwd}). Write inside the project you were launched in. If you truly need to touch another directory, ask the user.`,
  };
}

// Guard 3: catches a turn that ends with NO real tool call but assistant text shaped like
// one (Claude/Superpowers `<read>`, `<write>`, `<edit>`, `<bash>`, `<ls>`, `<dir>`, `<invoke>`, `<tool_code>` tags,
// or Markdown ` ```bash ` code blocks) — text that is never executed. Universal Parser intercepts valid tags and auto-advances.
const FAKE_TOOL_CALL_PATTERN = /<invoke\b|<\/invoke>|<parameter\s+name=|<\/?read-files?>|<modified-files>|<bash\b|<\/bash>|<read\b|<\/read>|<write\b|<\/write>|<edit\b|<\/edit>|<browse\b|<\/browse>|<ls\b|<\/ls>|<dir\b|<\/dir>|<tool_code\b|<\/tool_code>|<tool_call\b|<\/tool_call>|```(?:bash|sh|cmd|powershell|ps1)\b/i;

// A JSON payload shaped like a tool call — the shape a model reaches for when
// it "describes" tool calls instead of emitting them, e.g.
//   ```json
//   [{"tool": "Read", "arguments": {"path": "README.md"}}]
//   ```
// FAKE_TOOL_CALL_PATTERN misses this entirely: it only knows XML-ish tags and
// ```bash fences, so such a turn ended with zero tool calls, zero strikes and
// zero signal — the agent simply stalled. Both a name key AND an argument key
// are required so ordinary JSON the model prints as an *answer* (a config
// snippet, an API response) does not trip the guard.
const JSON_TOOL_NAME_KEY = /"(?:tool|tool_name|name|function|function_name|recipient_name)"\s*:\s*"[A-Za-z0-9_.\-]+"/i;
const JSON_TOOL_ARGS_KEY = /"(?:arguments|args|input|parameters|params|tool_input)"\s*:\s*[{[]/i;

function looksLikeJsonToolCall(text: string): boolean {
  return JSON_TOOL_NAME_KEY.test(text) && JSON_TOOL_ARGS_KEY.test(text);
}

function looksLikeFakeToolCall(text: string): boolean {
  return FAKE_TOOL_CALL_PATTERN.test(text) || looksLikeJsonToolCall(text);
}

// Pi's built-in tools, verified against the installed engine's
// dist/core/tools/*.js: bash, edit, find, grep, ls, read, write. Anything the
// auto-correction message names must be one of these — telling the model to
// call `read_file` (which does not exist in Pi) just produces another failed
// turn, which is how a single miss turns into a loop.
const PI_TOOLS = new Set(["bash", "edit", "find", "grep", "ls", "read", "write"]);

const TOOL_ALIASES: Record<string, string> = {
  read: "read", read_file: "read", readfile: "read", view: "read", cat: "read", open_file: "read", get_file: "read",
  write: "write", write_file: "write", writefile: "write", create_file: "write", create: "write", str_replace_editor: "edit",
  edit: "edit", edit_file: "edit", str_replace: "edit", apply_patch: "edit", replace: "edit",
  bash: "bash", shell: "bash", sh: "bash", run: "bash", run_command: "bash", command: "bash", terminal: "bash",
  execute: "bash", execute_command: "bash", exec: "bash", cmd: "bash", powershell: "bash",
  ls: "ls", dir: "ls", list: "ls", list_dir: "ls", list_files: "ls", listdirectory: "ls", list_directory: "ls",
  grep: "grep", search: "grep", ripgrep: "grep", rg: "grep", search_files: "grep", codebase_search: "grep",
  find: "find", glob: "find", file_search: "find", find_files: "find",
};

// Argument-key synonyms, normalized to the parameter names in Pi's schemas
// (read/write/edit/ls/grep/find take `path`; bash takes `command`; grep/find
// take `pattern`).
const ARG_ALIASES: Record<string, string> = {
  file_path: "path", filepath: "path", filename: "path", file: "path", absolute_path: "path",
  target_file: "path", dir: "path", directory: "path", folder: "path",
  cmd: "command", script: "command", shell_command: "command", commandline: "command",
  query: "pattern", regex: "pattern", search: "pattern",
  text: "content", contents: "content", body: "content", new_text: "content",
};

function canonicalizeToolName(name: string): string {
  const key = String(name).trim().toLowerCase().replace(/[\s-]+/g, "_");
  return TOOL_ALIASES[key] ?? key;
}

function canonicalizeArgs(toolName: string, args: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(args ?? {})) {
    const canonical = ARG_ALIASES[k.toLowerCase()] ?? k;
    // Never let an alias clobber a key the model already spelled correctly.
    if (!(canonical in out) || out[canonical] === undefined) out[canonical] = v;
  }
  // `ls` on a bare string arg, `bash` given a path, ... are left alone: fail
  // open and let the model re-issue rather than invent arguments.
  if (toolName === "ls" && typeof out.path !== "string" && typeof out.command === "string") {
    out.path = out.command;
    delete out.command;
  }
  return out;
}

interface ParsedToolTag {
  name: string;
  args: Record<string, unknown>;
  raw: string;
  /** How many tool calls the payload described; >1 means the model batched them. */
  count?: number;
  /** True when the canonical name is not one of Pi's built-in tools. */
  unknownTool?: boolean;
}

// Normalizes a raw {name, args} pair into Pi's tool vocabulary.
function toParsedTag(rawName: string, rawArgs: Record<string, unknown>, raw: string, count = 1): ParsedToolTag {
  const name = canonicalizeToolName(rawName);
  return { name, args: canonicalizeArgs(name, rawArgs), raw, count, unknownTool: !PI_TOOLS.has(name) };
}

// Extracts every tool-call-shaped object from a JSON payload, fenced or bare,
// object or array. Returns [] when nothing matches.
function extractJsonToolCalls(text: string): { name: string; args: Record<string, unknown> }[] {
  const candidates: string[] = [];
  const fenced = text.match(/```(?:json|tool|tool_call|tool_calls|toolcode)?\s*([\s\S]*?)```/gi) ?? [];
  for (const block of fenced) {
    candidates.push(block.replace(/^```[a-z_]*\s*/i, "").replace(/```$/, "").trim());
  }
  // Bare (unfenced) payloads too — some models drop the fence entirely. A
  // non-greedy regex is wrong here: it stops at the first `}`, which is the
  // *nested* arguments object, yielding invalid JSON. Scan for balanced
  // delimiters instead.
  candidates.push(...extractBalancedJsonSpans(text));

  for (const candidate of candidates) {
    let parsed: unknown;
    try {
      parsed = JSON.parse(candidate);
    } catch {
      continue;
    }
    const items = Array.isArray(parsed) ? parsed : [parsed];
    const calls: { name: string; args: Record<string, unknown> }[] = [];
    for (const item of items) {
      if (!item || typeof item !== "object") continue;
      const o = item as Record<string, unknown>;
      const nameRaw = o.tool ?? o.name ?? o.tool_name ?? o.function ?? o.function_name ?? o.recipient_name;
      const name = typeof nameRaw === "string" ? nameRaw : typeof (nameRaw as { name?: unknown })?.name === "string" ? (nameRaw as { name: string }).name : null;
      if (!name) continue;
      // An argument key is mandatory. Without it, `{"name": "my-skill",
      // "description": "..."}` — ordinary JSON a model prints as its ANSWER —
      // would be hijacked into a bogus tool call.
      const hasArgsKey = ["arguments", "args", "input", "parameters", "params", "tool_input"].some((k) => k in o);
      if (!hasArgsKey) continue;
      const argsRaw = o.arguments ?? o.args ?? o.input ?? o.parameters ?? o.params ?? o.tool_input ?? {};
      const args = (typeof argsRaw === "string" ? safeJsonObject(argsRaw) : argsRaw) as Record<string, unknown>;
      calls.push({ name, args: args && typeof args === "object" ? args : {} });
    }
    if (calls.length > 0) return calls;
  }
  return [];
}

// Returns each top-level {...} / [...] span in the text, delimiter-balanced and
// string-aware (so a `}` inside a JSON string value doesn't end the span).
//
// SCAN_BUDGET bounds the work: an unbalanced opener restarts the inner scan one
// character later, which is O(n²) on pathological input (a wall of `{`). This
// runs on every turn_end, so an unbounded scan would let one malformed message
// hang the whole session — the opposite of what a loop guard is for.
const JSON_SCAN_BUDGET = 200_000;

function extractBalancedJsonSpans(text: string, maxSpans = 5): string[] {
  const spans: string[] = [];
  let budget = JSON_SCAN_BUDGET;
  for (let i = 0; i < text.length && spans.length < maxSpans && budget > 0; i++) {
    const open = text[i];
    if (open !== "{" && open !== "[") continue;
    const close = open === "{" ? "}" : "]";
    let depth = 0;
    let inString = false;
    let escaped = false;
    for (let j = i; j < text.length && budget-- > 0; j++) {
      const ch = text[j];
      if (inString) {
        if (escaped) escaped = false;
        else if (ch === "\\") escaped = true;
        else if (ch === '"') inString = false;
        continue;
      }
      if (ch === '"') inString = true;
      else if (ch === open) depth++;
      else if (ch === close) {
        depth--;
        if (depth === 0) {
          spans.push(text.slice(i, j + 1));
          i = j;
          break;
        }
      }
    }
  }
  return spans;
}

function safeJsonObject(raw: string): Record<string, unknown> {
  try {
    const v = JSON.parse(raw);
    return v && typeof v === "object" ? (v as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

export function parseUniversalToolTag(text: string): ParsedToolTag | null {
  if (!text || typeof text !== "string") return null;

  // 0. JSON tool-call payloads (```json [{"tool": ..., "arguments": ...}] ```,
  //    a single object, fenced or bare). Checked first: it is the shape most
  //    local models fall back to, and the old parser only matched a fenced
  //    object whose FIRST key was literally "name".
  const jsonCalls = extractJsonToolCalls(text);
  if (jsonCalls.length > 0) {
    const first = jsonCalls[0];
    return toParsedTag(first.name, first.args, text.trim(), jsonCalls.length);
  }

  // 1. Standard XML tool wrappers: <tool_code>, <invoke>, <tool_call>, <function_call>, <action>, <execute>
  //    Fenced ```json payloads are NOT handled here: step 0 already covers
  //    them and enforces the "must carry an argument key" gate. The old
  //    fenced-object pattern here required no such gate, so it hijacked any
  //    ```json block whose first key happened to be "name" — e.g. a skill
  //    frontmatter snippet the model was legitimately showing the user.
  const tagPatterns = [
    /<(?:tool_code|invoke|tool_call|function_call|action|execute)\b[^>]*>([\s\S]*?)<\/(?:tool_code|invoke|tool_call|function_call|action|execute)>/i,
  ];

  for (const pattern of tagPatterns) {
    const match = text.match(pattern);
    if (match && match[1]) {
      const rawContent = match[1].trim();
      try {
        const parsed = JSON.parse(rawContent);
        if (parsed && typeof parsed === "object" && typeof parsed.name === "string") {
          const name = parsed.name;
          const args = (parsed.arguments || parsed.input || parsed.parameters || {}) as Record<string, unknown>;
          return toParsedTag(name, args, match[0]);
        }
      } catch {
        const nameMatch = text.match(/<invoke\s+name=["']([^"']+)["']/i) || text.match(/<tool_code\s+name=["']([^"']+)["']/i);
        if (nameMatch && nameMatch[1]) {
          return toParsedTag(nameMatch[1], {}, match[0]);
        }
      }
    }
  }

  // 2. Specific tool XML tags: <read>, <write>, <edit>, <bash>, <ls>, <dir>, <browse>, <search>, <command>, <terminal>, <read_file>, <write_file>
  const anthropicTagPattern = /<(read|write|edit|bash|ls|dir|browse|search|command|terminal|read_file|write_file)\b[^>]*>([\s\S]*?)<\/\1>/i;
  const matchAnthropic = text.match(anthropicTagPattern);
  if (matchAnthropic && matchAnthropic[1] && matchAnthropic[2]) {
    const tagName = matchAnthropic[1].toLowerCase();
    const rawBody = matchAnthropic[2].trim();

    // canonicalizeToolName covers read/read_file -> read, ls/dir -> ls,
    // command/terminal -> bash. `browse`/`search` have no built-in Pi
    // equivalent and stay as-is (flagged unknownTool by toParsedTag).
    const toolName = canonicalizeToolName(tagName);

    let args: Record<string, unknown> = {};
    if (rawBody.startsWith("{") && rawBody.endsWith("}")) {
      try { args = JSON.parse(rawBody); } catch {}
    }

    if (Object.keys(args).length === 0) {
      if (toolName === "bash") {
        args = { command: rawBody };
      } else if (toolName === "ls") {
        const pathMatch = rawBody.match(/"path"\s*:\s*"([^"]+)"/) || rawBody.match(/["']([^"']+)["']/);
        args = { path: pathMatch ? pathMatch[1] : (rawBody.trim() || ".") };
      } else if (toolName === "read") {
        const pathMatch = rawBody.match(/"(?:file_path|path|filePath|filename|file)"\s*:\s*"([^"]+)"/) || rawBody.match(/["']([^"']+)["']/);
        if (pathMatch) args = { path: pathMatch[1] };
        else args = { path: rawBody.trim() };
      } else if (toolName === "write" || toolName === "edit") {
        const pathMatch = rawBody.match(/"(?:file_path|path|filePath|filename|file)"\s*:\s*"([^"]+)"/);
        const path = pathMatch ? pathMatch[1] : "";
        args = { path, content: rawBody };
      }
    }

    return toParsedTag(toolName, args, matchAnthropic[0]);
  }

  // 3. Markdown Bash code blocks: ```bash command ``` or ```sh command ```
  const bashBlockPattern = /```(?:bash|sh|cmd|powershell|ps1)\s*([\s\S]*?)\s*```/i;
  const matchBashBlock = text.match(bashBlockPattern);
  if (matchBashBlock && matchBashBlock[1]) {
    const rawBody = matchBashBlock[1].trim();
    if (rawBody) {
      let toolName = "bash";
      let args: Record<string, unknown> = { command: rawBody };
      if (rawBody.startsWith("read ") || rawBody.startsWith("cat ")) {
        toolName = "read";
        const targetPath = rawBody.replace(/^(?:read|cat)\s+/, "").trim();
        args = { path: targetPath };
      }
      return toParsedTag(toolName, args, matchBashBlock[0]);
    }
  }

  // 4. Standalone JSON object in text with "name" and "arguments" / "path" / "command"
  const jsonMatch = text.match(/\{\s*"name"\s*:\s*"([a-zA-Z0-9_\-]+)"\s*,\s*"(?:arguments|input|parameters|path|command|file_path)"\s*:[\s\S]*?\}/);
  if (jsonMatch) {
    try {
      const parsed = JSON.parse(jsonMatch[0]);
      if (parsed && typeof parsed.name === "string") {
        const name = parsed.name;
        const args = (parsed.arguments || parsed.input || parsed.parameters || parsed) as Record<string, unknown>;
        delete args.name;
        return toParsedTag(name, args, jsonMatch[0]);
      }
    } catch {}
  }

  return null;
}

function extractMessageText(message: unknown): string {
  const content = (message as { content?: unknown } | undefined)?.content;
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";
  return content
    .filter((c): c is { text: string } => !!c && typeof (c as { text?: unknown }).text === "string")
    .map((c) => c.text)
    .join("\n");
}

// README documents `enableUniversalTagTransformer` and
// `enableSelfHealingLoopGuard` in pi-config/harness-config.json as the fix for
// "<tool_code> 標籤卡死 / 死鎖停擺". Until now nothing read either key: they were
// decorative, so following the documented remedy changed nothing. Both are
// honored here, defaulting to on (absent config == current behavior).
interface LoopGuardConfig {
  enableUniversalTagTransformer: boolean;
  enableSelfHealingLoopGuard: boolean;
}

// Deliberately NOT cached, matching taste-bridge / case-bridge /
// planning-with-files-bridge: every bridge re-reads harness-config.json per
// turn, so a flag edit takes effect on the next turn everywhere. A cache here
// would have made this one flag alone require a restart — and "I flipped the
// switch and nothing happened" is exactly the experience that made these flags
// look like zombies in the first place. The file is under 1KB.
function loopGuardConfig(): LoopGuardConfig {
  const config: LoopGuardConfig = { enableUniversalTagTransformer: true, enableSelfHealingLoopGuard: true };
  try {
    // import.meta.url, not require.resolve: Pi's loader shims `require` for
    // bridges, but bare `node` does not for an ESM-declared package — and
    // importing this file in node is how the guard gets behaviourally tested.
    // Under require.resolve the throw would be swallowed by this catch and
    // silently return the defaults, i.e. look exactly like a working config.
    const here = dirname(fileURLToPath(import.meta.url));
    const pkg = JSON.parse(readFileSync(join(here, "package.json"), "utf-8"));
    const harnessRoot = pkg["pi-harness"]?.root || join(here, "../..");
    const cfgPath = join(harnessRoot, "pi-config", "harness-config.json");
    if (existsSync(cfgPath)) {
      const cfg = JSON.parse(readFileSync(cfgPath, "utf8"));
      if (cfg.enableUniversalTagTransformer === false) config.enableUniversalTagTransformer = false;
      if (cfg.enableSelfHealingLoopGuard === false) config.enableSelfHealingLoopGuard = false;
    }
  } catch {}
  return config;
}

let consecutiveFakeToolStrikes = 0;
// The transformer used to reset consecutiveFakeToolStrikes on every hit, so a
// model that kept emitting parseable-but-fake calls could be auto-retried
// forever (each retry sets triggerTurn: true). This counter caps that path on
// its own budget and hands control back to the human at 3.
let consecutiveTransformStrikes = 0;
const MAX_RAW_ECHO = 400;

function loopGuard(event: { message: unknown; toolResults?: unknown[] }, ctx: ExtensionContext, pi: ExtensionAPI) {
  const hadRealToolCall = Array.isArray(event.toolResults) && event.toolResults.length > 0;
  if (hadRealToolCall) {
    consecutiveFakeToolStrikes = 0;
    consecutiveTransformStrikes = 0;
    return;
  }

  const cfg = loopGuardConfig();
  if (!cfg.enableSelfHealingLoopGuard && !cfg.enableUniversalTagTransformer) return;

  const text = extractMessageText(event.message);

  // Universal Tool Tag Transformer: intercept valid tool tags and auto-advance
  const parsedTag = cfg.enableUniversalTagTransformer ? parseUniversalToolTag(text) : null;
  if (parsedTag) {
    consecutiveFakeToolStrikes = 0;
    consecutiveTransformStrikes += 1;

    if (consecutiveTransformStrikes >= 3) {
      consecutiveTransformStrikes = 0;
      ctx.ui.notify("🚨 Universal Parser auto-corrected 3 turns in a row with no real tool call — handing back to the user.", "error");
      pi.sendMessage(
        {
          customType: "loop-guard",
          content:
            "系統已連續 3 次自動糾正你的假工具呼叫，但你仍然沒有發出真正的原生 Function Call。" +
            "請停止輸出任何工具標籤或 JSON 工具描述，改用文字向使用者說明你卡住的原因與需要什麼協助。",
          display: true,
        },
        { deliverAs: "followUp", triggerTurn: true },
      );
      return;
    }

    const rawEcho = parsedTag.raw.length > MAX_RAW_ECHO ? `${parsedTag.raw.slice(0, MAX_RAW_ECHO)}…（已截斷）` : parsedTag.raw;
    const batchNote =
      parsedTag.count && parsedTag.count > 1
        ? `\n（你一次描述了 ${parsedTag.count} 個工具呼叫。請先發出第一個，其餘的在後續回合逐一發出。）`
        : "";
    const unknownNote = parsedTag.unknownTool
      ? `\n⚠️ 注意：'${parsedTag.name}' 不是 Pi 的內建工具。可用的內建工具只有：${[...PI_TOOLS].join(", ")}。請改用其中最接近的一個。`
      : "";

    ctx.ui.notify(
      `🛠️ Universal Parser: transformed fake tool call into '${parsedTag.name}' (strike ${consecutiveTransformStrikes}/3)`,
      "info",
    );

    pi.sendMessage(
      {
        customType: "universal-tag-transformer",
        content:
          `[SYSTEM CRITICAL AUTO-CORRECTION]\n` +
          `偵測到你剛才用純文字（XML 標籤或 JSON）描述工具呼叫，而不是發出真正的呼叫。原始文字：\n${rawEcho}\n\n` +
          `系統已識別你的意圖為呼叫原生工具【${parsedTag.name}】，解析後的參數為：\n` +
          `${JSON.stringify(parsedTag.args, null, 2)}${batchNote}${unknownNote}\n\n` +
          `🔥【指令】：請你在此輪對話中【立即且只能】呼叫原生工具 '${parsedTag.name}'，傳入上述參數！` +
          `絕對不要再輸出任何 XML 標籤、\`\`\`json 工具清單或 \`\`\`bash 程式碼塊！`,
        display: true,
      },
      // MUST be "followUp", not "nextTurn". Pi's docs (docs/extensions.md) are
      // explicit: "nextTurn" is "queued for next user prompt, does not
      // interrupt or trigger anything", and `triggerTurn` is "only applied to
      // steer and followUp modes (ignored for nextTurn)".
      //
      // With "nextTurn" the correction sat in a queue until the human typed
      // again — so the transformer never auto-advanced anything. That is the
      // stall this guard exists to break: the agent emits a tag-shaped call,
      // the transformer "fires", and nothing happens until you press a key.
      // Commit 87abf09 added triggerTurn: true here believing it would take
      // effect; it was silently ignored for this delivery mode.
      //
      // Found by scripts/measure-triggers.py on its first real run: a --print
      // session emitted <tool_code> and the session ended with no correction
      // message recorded at all. The 3-strike escalation below always used
      // "followUp" and did work, which is why the failure hid — the loud path
      // functioned while the quiet, common path did not.
      { deliverAs: "followUp", triggerTurn: true }
    );
    return;
  }

  if (!cfg.enableSelfHealingLoopGuard) return;

  if (!looksLikeFakeToolCall(text)) {
    consecutiveFakeToolStrikes = 0;
    consecutiveTransformStrikes = 0;
    return;
  }

  ctx.ui.notify(
    `🚨 Turn ended with no real tool call, but text looks like a fake tool-call tag (strike ${consecutiveFakeToolStrikes + 1}/3).`,
    "error",
  );

  consecutiveFakeToolStrikes += 1;

  if (consecutiveFakeToolStrikes >= 3) {
    consecutiveFakeToolStrikes = 0;
    pi.sendMessage(
      {
        customType: "loop-guard",
        content:
          "系統偵測到：你連續 3 次的回覆都沒有呼叫真正的工具，卻寫出了格式如 ```bash 或 <read> 的標籤文字。" +
          "請直接停止輸出標籤與程式碼塊文字。如果你原本想讀檔或執行指令，請改用真正的原生工具呼叫；如果你不確定下一步，請告訴使用者你卡住的原因。",
        display: true,
      },
      { deliverAs: "followUp", triggerTurn: true },
    );
  } else {
    // Self-healing auto-retry on strike 1 & 2 to prevent deadlocks
    pi.sendMessage(
      {
        customType: "loop-guard",
        content:
          `[System Self-Healing Auto-Retry] 提醒：這輪回覆沒有真正呼叫工具，但文字包含工具標籤或 Markdown 程式碼塊（Strike ${consecutiveFakeToolStrikes}/3）。` +
          "請重新回覆並發起標準的原生 Function Call 呼叫工具。",
        display: true,
      },
      // "followUp", not "nextTurn": this is the *auto-retry* on strikes 1 and 2.
      // Queued for the next user prompt it retries nothing on its own — the
      // agent stays stalled until a human types, which is the exact failure the
      // self-healing path exists to prevent.
      { deliverAs: "followUp", triggerTurn: true },
    );
  }
}

export default function (pi: ExtensionAPI) {
  pi.on("before_agent_start", (event, _ctx) => {
    let rawPrompt = event.systemPrompt ?? "";

    // Sanitize XML tag tool instructions introduced by third-party packages (e.g. superpowers)
    // to prevent local GGUF models from imitating XML text tags.
    rawPrompt = rawPrompt.replace(/<(?:read|write|edit|bash|ls|dir|browse|search)>\s*[\s\S]*?<\/(?:read|write|edit|bash|ls|dir|browse|search)>/gi, "");

    return {
      systemPrompt: rawPrompt + "\n\n" +
        "============================================================\n" +
        "[CRITICAL SYSTEM PROTOCOL: NATIVE TOOL CALLING ONLY]\n" +
        "• You MUST execute all actions using native JSON function calling (tool_call).\n" +
        "• NEVER output bash commands or tool calls inside markdown code blocks (e.g. ```bash) or XML tags (<read>, <write>, <bash>, <ls>).\n" +
        "• Text code blocks and XML tags are NOT executed by the system and will cause execution to halt.\n" +
        "============================================================\n"
    };
  });

  pi.on("tool_call", async (event, ctx) => {
    const runaway = runawayArgumentGuard(event, ctx);
    if (runaway) return runaway;
    if (event.toolName === "bash") return bashGuard(event, ctx);
    if (event.toolName === "write" || event.toolName === "edit") return containmentGuard(event, ctx);
  });

  pi.on("turn_end", async (event, ctx) => loopGuard(event as { message: unknown; toolResults?: unknown[] }, ctx, pi));
}
