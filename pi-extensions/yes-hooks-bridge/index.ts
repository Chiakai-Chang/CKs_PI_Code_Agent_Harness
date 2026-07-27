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
  if (inside) return;
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

interface ParsedToolTag {
  name: string;
  args: Record<string, unknown>;
  raw: string;
}

function parseUniversalToolTag(text: string): ParsedToolTag | null {
  if (!text || typeof text !== "string") return null;

  // 1. Standard XML tool wrappers: <tool_code>, <invoke>, <tool_call>, <function_call>, <action>, <execute>
  const tagPatterns = [
    /<(?:tool_code|invoke|tool_call|function_call|action|execute)\b[^>]*>([\s\S]*?)<\/(?:tool_code|invoke|tool_call|function_call|action|execute)>/i,
    /```(?:json|tool|tool_call)?\s*(\{\s*"name"\s*:\s*[\s\S]*?\})\s*```/i
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
          return { name, args, raw: match[0] };
        }
      } catch {
        const nameMatch = text.match(/<invoke\s+name=["']([^"']+)["']/i) || text.match(/<tool_code\s+name=["']([^"']+)["']/i);
        if (nameMatch && nameMatch[1]) {
          return { name: nameMatch[1], args: {}, raw: match[0] };
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

    let toolName = tagName;
    if (tagName === "read" || tagName === "read_file") toolName = "read_file";
    else if (tagName === "write" || tagName === "write_file") toolName = "write";
    else if (tagName === "edit") toolName = "edit";
    else if (tagName === "ls" || tagName === "dir") toolName = "bash";
    else if (tagName === "command" || tagName === "terminal") toolName = "bash";

    let args: Record<string, unknown> = {};
    if (rawBody.startsWith("{") && rawBody.endsWith("}")) {
      try { args = JSON.parse(rawBody); } catch {}
    }

    if (Object.keys(args).length === 0) {
      if (toolName === "bash") {
        if (tagName === "ls" || tagName === "dir") {
          const pathMatch = rawBody.match(/"path"\s*:\s*"([^"]+)"/) || rawBody.match(/["']([^"']+)["']/);
          const dirPath = pathMatch ? pathMatch[1] : (rawBody.trim() || ".");
          args = { command: `dir "${dirPath}"` };
        } else {
          args = { command: rawBody };
        }
      } else if (toolName === "read_file") {
        const pathMatch = rawBody.match(/"(?:file_path|path|filePath|filename|file)"\s*:\s*"([^"]+)"/) || rawBody.match(/["']([^"']+)["']/);
        if (pathMatch) args = { path: pathMatch[1] };
        else args = { path: rawBody.trim() };
      } else if (toolName === "write" || toolName === "edit") {
        const pathMatch = rawBody.match(/"(?:file_path|path|filePath|filename|file)"\s*:\s*"([^"]+)"/);
        const path = pathMatch ? pathMatch[1] : "";
        args = { path, content: rawBody };
      }
    }

    // Standardize keys for read_file
    if (toolName === "read_file" && !args.path) {
      const p = args.file_path || args.filePath || args.filename || args.file;
      if (typeof p === "string") args.path = p;
    }

    return { name: toolName, args, raw: matchAnthropic[0] };
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
        toolName = "read_file";
        const targetPath = rawBody.replace(/^(?:read|cat)\s+/, "").trim();
        args = { path: targetPath };
      }
      return { name: toolName, args, raw: matchBashBlock[0] };
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
        if (name === "read" || name === "read_file") {
          if (!args.path && args.file_path) args.path = args.file_path;
        }
        return { name, args, raw: jsonMatch[0] };
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

let consecutiveFakeToolStrikes = 0;

function loopGuard(event: { message: unknown; toolResults?: unknown[] }, ctx: ExtensionContext, pi: ExtensionAPI) {
  const hadRealToolCall = Array.isArray(event.toolResults) && event.toolResults.length > 0;
  if (hadRealToolCall) {
    consecutiveFakeToolStrikes = 0;
    return;
  }

  const text = extractMessageText(event.message);

  // Universal Tool Tag Transformer: intercept valid tool tags and auto-advance
  const parsedTag = parseUniversalToolTag(text);
  if (parsedTag) {
    consecutiveFakeToolStrikes = 0;
    ctx.ui.notify(`🛠️ Universal Parser: Transformed text tag <${parsedTag.name}>`, "info");

    pi.sendMessage(
      {
        customType: "universal-tag-transformer",
        content:
          `[SYSTEM CRITICAL AUTO-CORRECTION]\n` +
          `偵測到你剛才使用了純文字/XML標籤：<${parsedTag.name}> (原始文字：${parsedTag.raw})\n` +
          `系統已自動識別你的意圖為呼叫原生工具【${parsedTag.name}】，解析後的參數為：\n` +
          `${JSON.stringify(parsedTag.args, null, 2)}\n\n` +
          `🔥【指令】：請你在此輪對話中【立即且只能】呼叫原生工具 '${parsedTag.name}'，傳入上述參數！` +
          `絕對不要再輸出任何 XML 標籤或 \`\`\`bash 程式碼塊！`,
        display: true,
      },
      { deliverAs: "nextTurn" }
    );
    return;
  }

  if (!FAKE_TOOL_CALL_PATTERN.test(text)) {
    consecutiveFakeToolStrikes = 0;
    return;
  }

  consecutiveFakeToolStrikes += 1;
  ctx.ui.notify(
    `🚨 Turn ended with no real tool call, but text looks like a fake tool-call tag (strike ${consecutiveFakeToolStrikes}/3).`,
    "error",
  );

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
      { deliverAs: "followUp" },
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
      { deliverAs: "nextTurn" },
    );
  }
}

export default function (pi: ExtensionAPI) {
  pi.on("before_agent_start", (event, _ctx) => {
    return {
      systemPrompt: (event.systemPrompt ?? "") + "\n\n" +
        "============================================================\n" +
        "[CRITICAL SYSTEM PROTOCOL: NATIVE TOOL CALLING ONLY]\n" +
        "• You MUST execute all actions using native JSON function calling (tool_call).\n" +
        "• NEVER output bash commands or tool calls inside markdown code blocks (e.g. ```bash) or XML tags (<read>, <write>, <bash>, <ls>).\n" +
        "• Text code blocks and XML tags are NOT executed by the system and will cause execution to halt.\n" +
        "============================================================\n"
    };
  });

  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName === "bash") return bashGuard(event, ctx);
    if (event.toolName === "write" || event.toolName === "edit") return containmentGuard(event, ctx);
  });

  pi.on("turn_end", async (event, ctx) => loopGuard(event as { message: unknown; toolResults?: unknown[] }, ctx, pi));
}
