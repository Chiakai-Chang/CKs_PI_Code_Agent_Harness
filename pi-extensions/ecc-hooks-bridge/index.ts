/**
 * ECC Hooks Bridge Extension
 *
 * Maps ECC (everything-claude-code) hooks into pi's extension event system.
 * Invokes ECC's existing hook scripts when their matchers fire.
 *
 * Profile: standard (configurable via ECC_HOOK_PROFILE)
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { isToolCallEventType } from "@earendil-works/pi-coding-agent";

import { join, dirname } from "node:path";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";

import { AdvisoryQueue, advisoryResult } from "./advisory.ts";
import { hasAnyPlan, isGitCommit } from "./plan.ts";

// Dynamic path resolution
// Read from our own package.json which restore.py will patch
const pkgPath = require.resolve("./package.json");
const pkg = JSON.parse(readFileSync(pkgPath, "utf-8"));
const HARNESS_ROOT = pkg["pi-harness"]?.root || join(dirname(pkgPath), "../..");
const PROJECT_ROOT = HARNESS_ROOT;
const ECC_ROOT = join(PROJECT_ROOT, "external/ecc");

/**
 * What the model is told when a commit has no plan behind it.
 *
 * The previous wording ended with "建議使用 /plan". There is no `/plan` command:
 * `~/.pi/agent/commands/` does not exist, this bridge registers no commands, and
 * the only `plan.md` command files in the tree sit inside submodules that are
 * never installed. Naming the skill instead of a command keeps the advice
 * reachable however skills happen to be registered.
 */
const PLAN_ADVISORY =
  "You are committing with no task_plan.md in this project. If this is multi-step " +
  "work, use the planning-with-files skill to record the plan before continuing. " +
  "If it is a one-off change, say so and carry on — this is a prompt to decide, not a block.";

/**
 * Where the session is, which is not necessarily where Pi was launched.
 * Hook scripts ran in `process.cwd()` and so audited whatever directory the
 * binary happened to start in. Every other bridge uses `ctx.cwd`; session_start
 * records it here because runHookScript has no context to ask.
 */
let sessionCwd = process.cwd();

function getProfile(): "minimal" | "standard" | "strict" {
  const env = process.env.ECC_HOOK_PROFILE?.trim().toLowerCase();
  if (env === "minimal" || env === "standard" || env === "strict") return env;
  return "standard";
}

function shouldEnable(_id: string, profiles?: string): boolean {
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
  const fullPath = join(ECC_ROOT, script);
  const timeout = options?.timeout ?? 15000;

  return new Promise((resolve) => {
    if (!existsSync(fullPath)) {
      resolve({ stdout: "", stderr: `[ecc-bridge] Hook script not found: ${fullPath}\n`, exitCode: 0 });
      return;
    }

    const proc = spawn("node", [fullPath, ...args], {
      cwd: sessionCwd,
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
    proc.on("error", (err) => {
      resolve({ stdout: "", stderr: `[ecc-bridge] Spawn error: ${err.message}\n`, exitCode: 0 });
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
  // Findings that belong to the model rather than to the terminal. `notify`
  // paints the TUI and stops there, `ToolCallEventResult` has no channel but
  // `block`, and `turn_end` declares no result type at all — so a finding is
  // queued where it is produced and handed over at the next event that can carry
  // it. See advisory.ts for the type references this is built on.
  const advisories = new AdvisoryQueue();

  pi.on("session_start", async (_event, ctx) => {
    const profile = getProfile();
    sessionCwd = ctx.cwd;
    // The queue outlives a session; the session's findings must not.
    advisories.reset();
    ctx.ui.setStatus("ecc", `ECC bridge (profile: ${profile})`);

    // Health Probe
    if (!existsSync(ECC_ROOT)) {
      ctx.ui.notify(`⚠️ [ECC Bridge] 子模組缺失。請執行 git submodule update --init`, "warning");
    } else {
      try {
        const versionPath = join(ECC_ROOT, "VERSION");
        if (existsSync(versionPath)) {
          const version = readFileSync(versionPath, "utf-8").trim();
          console.log(`[ecc-bridge] ECC Submodule Version: ${version}`);
        }
      } catch {}
    }
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

    // Planning awareness: a commit with no plan behind it.
    //
    // Three things were wrong with the old version of this. It looked only in the
    // repo root while planning-with-files-bridge also honours `.planning/`, so a
    // plan kept there drew the nag anyway. It matched `includes("git commit")`,
    // which fired on any command that merely said the words. And it pointed at
    // `/plan`, which is not a command this harness installs.
    try {
      if (!hasAnyPlan(ctx.cwd) && isGitCommit(event.input.command)) {
        if (advisories.push("plan-missing", PLAN_ADVISORY, "once")) {
          ctx.ui.notify(`💡 偵測到提交操作，但尚未建立 task_plan.md。`, "info");
        }
      }
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
        if (lines.length) {
          ctx.ui.notify(lines.join(" "), "warning");
          // Below the blocking threshold the guard still has something to say,
          // and the model is the one that has to act on it.
          if (r.exitCode !== 2) {
            advisories.push("gateguard", `ECC GateGuard: ${lines.join(" ")}`, { cooldown: 3 });
          }
        }
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
        const text = r.stderr.trim().split("\n").slice(0, 2).join(" ");
        ctx.ui.notify(text, "info");
        // Only the model can decide a good moment to compact, and only it knows
        // what is still unfinished. Telling the terminal instead was pointless.
        advisories.push("suggest-compact", text, { cooldown: 10 });
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

    // Hand over whatever the pre-bash hooks queued for this command.
    return advisoryResult(event.content, advisories.drain()) ?? undefined;
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
        if (lines.length) {
          ctx.ui.notify(lines.join(" "), "warning");
          // The gate describes the edit that just happened. Sending it to the
          // terminal meant the model kept building on an edit it had been told
          // was bad — by a channel it cannot read.
          advisories.push("quality-gate", `ECC quality-gate: ${lines.join(" ")}`, "always");
        }
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
      if (r.stderr) {
        const text = r.stderr.trim().split("\n").slice(0, 2).join(" ");
        ctx.ui.notify(text, "warning");
        advisories.push("console-warn", `ECC console check: ${text}`, "always");
      }
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

    return advisoryResult(event.content, advisories.drain()) ?? undefined;
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
        if (lines.length) {
          ctx.ui.notify(lines.join(" "), "warning");
          // turn_end has no result type (types.d.ts:876), so this cannot be
          // handed over here. It waits for the next tool result or turn start.
          advisories.push("format-typecheck", `ECC format/typecheck: ${lines.join(" ")}`, "always");
        }
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

    // hello-reflect: auto-detect learnings (distilled from claude-reflect)
    try {
      const { execSync } = await import("node:child_process");
      const python = process.platform === "win32" ? "python" : "python3";
      const captureScript = join(PROJECT_ROOT, "pi-skills/core/hello-reflect/scripts/capture.py");
      
      const homeDir = process.env.HOME || process.env.USERPROFILE || "";
      const sessionsDir = join(homeDir, ".pi/agent/sessions");
      
      if (existsSync(sessionsDir)) {
        // Recursively find the newest modified .jsonl file in the sessions directory
        let latestFile: string | null = null;
        let latestTime = 0;
        
        const traverse = (currentDir: string) => {
          if (!existsSync(currentDir)) return;
          const entries = readdirSync(currentDir, { withFileTypes: true });
          for (const entry of entries) {
            const fullPath = join(currentDir, entry.name);
            if (entry.isDirectory()) {
              traverse(fullPath);
            } else if (entry.isFile() && entry.name.endsWith(".jsonl")) {
              try {
                const mtime = statSync(fullPath).mtime.getTime();
                if (mtime > latestTime) {
                  latestTime = mtime;
                  latestFile = fullPath;
                }
              } catch {}
            }
          }
        };
        
        traverse(sessionsDir);
        
        if (latestFile) {
          const result = execSync(`"${python}" "${captureScript}" "${latestFile}"`, { encoding: "utf-8" });
          if (result.trim() && result.startsWith("[")) {
            const learnings = JSON.parse(result);
            if (learnings.length > 0) {
              // Was "執行 /hello-reflect": no such command, and the skill is
              // reachable only by name. Naming the skill keeps the advice valid.
              ctx.ui.notify(`📝 偵測到新學習點 (${learnings.length})。`, "info");
              advisories.push(
                "hello-reflect",
                `${learnings.length} new learning(s) were detected in this session. ` +
                  `Use the hello-reflect skill to fold them into the project rules.`,
                "once",
              );
            }
          }
        }
      }
    } catch {}
  });

  // ========== Backstop delivery ==========
  //
  // Findings produced at turn_end have no channel where they are made, and a
  // session can end its turn without another tool call ever happening. This is
  // the one event that always runs before the model thinks again.
  pi.on("before_agent_start", (event) => {
    const pending = advisories.drain();
    if (!pending) return;
    return { systemPrompt: (event.systemPrompt ?? "") + "\n\n" + pending };
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
