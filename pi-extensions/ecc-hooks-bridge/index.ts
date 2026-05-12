/**
 * ECC Hooks Bridge Extension
 *
 * Maps ECC (everything-claude-code) hooks into pi's extension event system.
 * Invokes ECC's existing hook scripts when their matchers fire.
 *
 * Profile: standard (configurable via ECC_HOOK_PROFILE)
 */
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { isToolCallEventType } from "@mariozechner/pi-coding-agent";

import { join, dirname } from "node:path";
import { existsSync, readFileSync } from "node:fs";

// Dynamic path resolution
// Read from our own package.json which restore.py will patch
const pkgPath = require.resolve("./package.json");
const pkg = JSON.parse(readFileSync(pkgPath, "utf-8"));
const HARNESS_ROOT = pkg["pi-harness"]?.root || join(dirname(pkgPath), "../..");
const PROJECT_ROOT = HARNESS_ROOT;
const ECC_ROOT = join(PROJECT_ROOT, "external/everything-claude-code");

// Verify ECC exists
if (!existsSync(ECC_ROOT)) {
  console.warn(`[ecc-bridge] ECC not found. Run: git submodule update --init`);
}

function getProfile(): "minimal" | "standard" | "strict" {
  const env = process.env.ECC_HOOK_PROFILE?.trim().toLowerCase();
  if (env === "minimal" || env === "standard" || env === "strict") return env;
  return "standard";
}

function shouldEnable(id: string, profiles?: string): boolean {
  if (!profiles) return true;
  const profile = getProfile();
  return profiles.split(",").some(p => p.trim() === profile);
}

async function runHookScript(
  script: string,
  args: string[],
  input: string,
  options?: { timeout?: number; async?: boolean; profiles?: string }
): Promise<{ stdout: string; stderr: string; exitCode: number }> {
  if (options?.profiles && !shouldEnable(script, options.profiles)) {
    return { stdout: "", stderr: "", exitCode: 0 };
  }

  const { spawn } = await import("node:child_process");
  const fullPath = ECC_ROOT + "/" + script;
  const timeout = options?.timeout ?? 15000;

  return new Promise((resolve) => {
    const proc = spawn("node", [fullPath, ...args], {
      cwd: process.cwd(),
      timeout,
      env: { ...process.env, CLAUDE_PLUGIN_ROOT: ECC_ROOT },
    });

    let stdout = "";
    let stderr = "";

    proc.stdin.write(input);
    proc.stdin.end();
    proc.stdout.on("data", (d: Buffer) => { stdout += d.toString(); });
    proc.stderr.on("data", (d: Buffer) => { stderr += d.toString(); });
    proc.on("exit", (code) => {
      resolve({ stdout, stderr, exitCode: code ?? 0 });
    });
    proc.on("error", () => {
      resolve({ stdout: "", stderr: `[ecc-bridge] Hook script error: ${script}\n`, exitCode: 0 });
    });
  });
}

async function runWithFlags(
  hookId: string,
  script: string,
  input: string,
  options?: { timeout?: number; profiles?: string }
): Promise<{ stdout: string; stderr: string; exitCode: number }> {
  const runner = "scripts/hooks/run-with-flags.js";
  const profiles = options?.profiles ?? "standard,strict";
  return await runHookScript(runner, [hookId, script, profiles], input, {
    timeout: options?.timeout ?? 15000,
  });
}

export default function (pi: ExtensionAPI) {
  pi.on("session_start", async (_event, ctx) => {
    const profile = getProfile();
    ctx.ui.setStatus("ecc", `ECC bridge (profile: ${profile})`);
  });

  // ========== PreToolUse: Bash ==========
  pi.on("tool_call", async (event, ctx) => {
    if (!isToolCallEventType("bash", event)) return;
    const input = JSON.stringify(event.input);

    // block-no-verify: prevent git push --no-verify
    try {
      const r = await runHookScript(
        "scripts/hooks/block-no-verify.js",
        [],
        input,
        { profiles: "minimal,standard,strict", timeout: 3000 }
      );
      if (r.stderr) ctx.ui.notify(r.stderr.trim().split("\n").slice(0, 2).join(" "), "warning");
      if (r.exitCode === 2) return { block: true, reason: "Blocked by ECC block-no-verify" };
    } catch {}

    // GateGuard fact-force: demand investigation before edits
    try {
      const r = await runWithFlags(
        "pre:bash:gateguard-fact-force",
        "scripts/hooks/gateguard-fact-force.js",
        input,
        { profiles: "standard,strict", timeout: 5000 }
      );
      if (r.stderr) {
        const lines = r.stderr.trim().split("\n").slice(0, 3);
        if (lines.length) ctx.ui.notify(lines.join(" "), "warning");
      }
      if (r.exitCode === 2) return { block: true, reason: "ECC GateGuard: investigate first" };
    } catch {}
  });

  // ========== PreToolUse: Edit / Write ==========
  pi.on("tool_call", async (event, ctx) => {
    const name = event.toolName;
    if (!["edit", "write"].includes(name)) return;
    const input = JSON.stringify({ tool_name: name, tool_input: event.input });

    // doc-file-warning
    try {
      await runWithFlags(
        "pre:write:doc-file-warning",
        "scripts/hooks/doc-file-warning.js",
        input,
        { profiles: "standard,strict", timeout: 5000 }
      );
    } catch {}

    // suggest-compact at intervals
    try {
      const r = await runWithFlags(
        "pre:edit-write:suggest-compact",
        "scripts/hooks/suggest-compact.js",
        input,
        { profiles: "standard,strict", timeout: 5000 }
      );
      if (r.stderr?.includes("compact")) {
        ctx.ui.notify(r.stderr.trim().split("\n").slice(0, 2).join(" "), "info");
      }
    } catch {}

    // config-protection: block config weakening
    try {
      const r = await runWithFlags(
        "pre:config-protection",
        "scripts/hooks/config-protection.js",
        input,
        { profiles: "standard,strict", timeout: 5000 }
      );
      if (r.stderr) ctx.ui.notify(r.stderr.trim().split("\n").slice(0, 2).join(" "), "warning");
      if (r.exitCode === 2) return { block: true, reason: "ECC: config protection" };
    } catch {}
  });

  // ========== PostToolUse: Bash ==========
  pi.on("tool_result", async (event, ctx) => {
    if (event.toolName !== "bash") return;
    const output = Array.isArray(event.content)
      ? event.content.map(c => typeof c === "object" && "text" in c ? c.text : "").join("")
      : String(event.content ?? "");
    const input = JSON.stringify({
      tool_name: "bash",
      tool_input: event.input,
      tool_output: { output },
    });

    // Post-bash: PR created / build complete / command log (async)
    try {
      await runHookScript(
        "scripts/hooks/post-bash-dispatcher.js",
        [],
        input,
        { profiles: "standard,strict", timeout: 30000 }
      );
    } catch {}
  });

  // ========== PostToolUse: Edit ==========
  pi.on("tool_result", async (event, ctx) => {
    const name = event.toolName;
    if (!["edit", "write"].includes(name)) return;
    const input = JSON.stringify({
      tool_name: name,
      tool_input: event.input,
      tool_output: event.content ?? "",
    });

    // quality-gate (async)
    try {
      const r = await runWithFlags(
        "post:quality-gate",
        "scripts/hooks/quality-gate.js",
        input,
        { profiles: "standard,strict", timeout: 30000 }
      );
      if (r.stderr) {
        const lines = r.stderr.trim().split("\n").slice(0, 4);
        if (lines.length) ctx.ui.notify(lines.join(" "), "warning");
      }
    } catch {}

    // design-quality-check
    try {
      await runWithFlags(
        "post:edit:design-quality-check",
        "scripts/hooks/design-quality-check.js",
        input,
        { profiles: "standard,strict", timeout: 10000 }
      );
    } catch {}

    // console-warn
    try {
      const r = await runWithFlags(
        "post:edit:console-warn",
        "scripts/hooks/post-edit-console-warn.js",
        input,
        { profiles: "standard,strict", timeout: 5000 }
      );
      if (r.stderr) ctx.ui.notify(r.stderr.trim().split("\n").slice(0, 2).join(" "), "warning");
    } catch {}

    // post-edit-accumulator
    try {
      await runWithFlags(
        "post:edit:accumulator",
        "scripts/hooks/post-edit-accumulator.js",
        input,
        { profiles: "standard,strict", timeout: 5000 }
      );
    } catch {}
  });

  // ========== Stop (turn_end): batch format+typecheck / console audit ==========
  pi.on("turn_end", async (_event, ctx) => {
    const profile = getProfile();
    if (profile === "minimal") return;

    const turnData = JSON.stringify({
      timestamp: Date.now(),
      profile,
      cwd: ctx.cwd,
    });

    // stop:format-typecheck (batch)
    try {
      const r = await runWithFlags(
        "stop:format-typecheck",
        "scripts/hooks/stop-format-typecheck.js",
        turnData,
        { profiles: "standard,strict", timeout: 120000 }
      );
      if (r.stderr) {
        const lines = r.stderr.trim().split("\n").slice(0, 6);
        if (lines.length) ctx.ui.notify(lines.join(" "), "warning");
      }
    } catch {}

    // stop:check-console-log
    try {
      await runWithFlags(
        "stop:check-console-log",
        "scripts/hooks/check-console-log.js",
        turnData,
        { profiles: "standard,strict", timeout: 30000 }
      );
    } catch {}

    // stop:session-end (persist state)
    try {
      await runWithFlags(
        "stop:session-end",
        "scripts/hooks/session-end.js",
        turnData,
        { profiles: "minimal,standard,strict", timeout: 30000 }
      );
    } catch {}

    // stop:evaluate-session (continuous learning)
    try {
      await runWithFlags(
        "stop:evaluate-session",
        "scripts/hooks/evaluate-session.js",
        turnData,
        { profiles: "minimal,standard,strict", timeout: 30000 }
      );
    } catch {}
  });

  // ========== PreCompact ==========
  pi.on("session_before_compact", async (_event, ctx) => {
    try {
      const turnData = JSON.stringify({ timestamp: Date.now(), profile: getProfile() });
      await runWithFlags(
        "pre:compact",
        "scripts/hooks/pre-compact.js",
        turnData,
        { profiles: "standard,strict", timeout: 10000 }
      );
    } catch {}
  });
}
 {}
  });
}
