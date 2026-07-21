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
// one (Claude-style `<invoke>`/`<parameter name=`, or ad-hoc `<read-files>`/`<bash><command>`
// tags) — text that is never executed. Pi's own compaction summary format legitimately ends
// with literal `<read-files>`/`<modified-files>` tags (see compaction.md); a weak local model
// can echo that shape right back as if it were an action to take, then loop on its own echo
// across turns since nothing else interrupts it. Structurally invisible to `tool_call` hooks
// (no tool_call event fires for plain text), so this hooks `turn_end` instead. Implements
// AGENTS.md §4's "3-Strike Cap" as code instead of unenforced prose.
const FAKE_TOOL_CALL_PATTERN = /<invoke\b|<\/invoke>|<parameter\s+name=|<\/?read-files?>|<modified-files>|<bash>\s*<command>/i;

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
          "系統偵測到：你連續 3 次的回覆都沒有呼叫真正的工具，卻寫出了看起來像工具呼叫的標籤文字（例如 <invoke>、<read-file>、<bash>）。" +
          "那些文字不會被執行——工具呼叫必須透過真正的 function-calling 機制，不是印出 XML／標籤文字。" +
          "現在請直接停下：不要再輸出任何 <invoke>／<read-file>／<bash> 之類的標籤。" +
          "如果你原本想讀檔或執行指令，請改用真正的工具呼叫；如果你不確定下一步，直接用一般文字告訴使用者你卡住的原因並停止，等待使用者指示。",
        display: true,
      },
      { deliverAs: "nextTurn" },
    );
  } else {
    pi.sendMessage(
      {
        customType: "loop-guard",
        content:
          "提醒：這輪回覆沒有真正呼叫工具，但文字內容像是工具呼叫標籤（如 <invoke>／<read-file>／<bash>）——那些是純文字，不會被執行。" +
          "若要用工具，請使用真正的工具呼叫機制；若沒有下一步，直接說明並停止，不要再輸出這類標籤。",
        display: true,
      },
      { deliverAs: "nextTurn" },
    );
  }
}

export default function (pi: ExtensionAPI) {
  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName === "bash") return bashGuard(event, ctx);
    if (event.toolName === "write" || event.toolName === "edit") return containmentGuard(event, ctx);
  });

  pi.on("turn_end", async (event, ctx) => loopGuard(event as { message: unknown; toolResults?: unknown[] }, ctx, pi));
}
