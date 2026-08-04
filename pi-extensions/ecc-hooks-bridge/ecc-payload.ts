/**
 * Pi events in, ECC hook contract out — and back again.
 *
 * Fifteen ECC hooks are wired into this bridge and exactly one of them worked.
 * `block-no-verify` scans raw text, so shape never mattered to it. The rest were
 * handed a payload they could not read, and two of them answered on a channel
 * nobody was listening to. Measured 2026-08-04 against the installed Pi and the
 * vendored ECC:
 *
 *   dist/core/tools/write.d.ts:5   path: TString;  content: TString
 *   dist/core/tools/edit.d.ts:11   path: TString;  edits: [{oldText,newText}]
 *
 *   post-edit-console-warn.js:28   input.tool_input?.file_path
 *   quality-gate.js:143            input.tool_input?.file_path
 *   config-protection.js:93        tool_input?.file_path || tool_input?.file
 *   gateguard-fact-force.js:1145   data.tool_name / data.tool_input
 *
 * `external/ecc` is a submodule, and yes-hooks-bridge blocks writes into vendored
 * submodules anyway, so the translation belongs here rather than upstream. ECC's
 * contract is treated as a fixed external interface.
 */

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

/**
 * Whether GateGuard is allowed to actually block, rather than only advise.
 *
 * Repairing the translation switches this gate on for the first time on this
 * machine, and it is a fact-forcing gate rather than a destructive-command
 * filter: measured against the real hook, it denies the FIRST bash command of
 * every session whatever it is — `ls -la` and `echo hi` included. A hard block on
 * turn one, on a weak local model, is not something to inherit by accident.
 *
 * Fails CLOSED, unlike the advisory switch: an unreadable config must not turn
 * this on.
 */
export function gateGuardBlocksEnabled(harnessRoot: string): boolean {
  try {
    const cfgPath = join(harnessRoot, "pi-config", "harness-config.json");
    if (!existsSync(cfgPath)) return false;
    return JSON.parse(readFileSync(cfgPath, "utf8"))["enableEccGateGuard"] === true;
  } catch {
    return false;
  }
}

/** The Claude-Code-shaped payload every ECC hook parses. */
export interface EccHookInput {
  tool_name: string;
  tool_input: Record<string, unknown>;
  tool_output?: { output: string };
}

/**
 * Build what the hook reads from what Pi hands us.
 *
 * `file_path` is the field every ECC hook looks for; Pi calls it `path`. Both are
 * sent: the extra field costs nothing and means an upstream that starts reading
 * `path` will not break this a second time.
 *
 * `tool_name` stays lowercase — gateguard-fact-force.js:1148 maps it through a
 * case-insensitive TOOL_MAP.
 */
export function toHookInput(
  toolName: string,
  input: Record<string, unknown> | null | undefined,
  output?: { output: string } | null,
): EccHookInput {
  const src = (input && typeof input === "object") ? input : {};
  const tool_input: Record<string, unknown> = { ...src };

  if (typeof src.path === "string" && src.path) {
    tool_input.file_path = src.path;
  }

  const built: EccHookInput = { tool_name: toolName, tool_input };
  if (output && typeof output.output === "string") {
    built.tool_output = { output: output.output };
  }
  return built;
}

/** What a hook decided, in terms this bridge acts on. */
export interface HookDecision {
  block?: boolean;
  reason?: string;
  advisory?: string;
}

interface RawHookResult {
  stdout?: string;
  stderr?: string;
  exitCode?: number;
}

/**
 * Read a hook's answer off whichever channel it used.
 *
 * Three are in play. `exit(2)` is what block-no-verify and config-protection use.
 * `hookSpecificOutput.permissionDecision` on stdout with exitCode 0 is what
 * gateguard-fact-force uses — the bridge only checked exitCode 2, so that gate
 * never closed. `hookSpecificOutput.additionalContext` on stdout is what
 * suggest-compact uses, and its own comment explains why: non-blocking stderr
 * reaches the debug log, not the model.
 *
 * Hooks echo their input back on stdout when they have no opinion. Requiring a
 * parsed `hookSpecificOutput` before reading anything from stdout keeps that
 * pass-through from being served to the model as advice.
 */
export function parseHookOutput(result: RawHookResult): HookDecision {
  const stderr = (result?.stderr ?? "").trim();
  const stdout = (result?.stdout ?? "").trim();

  if (result?.exitCode === 2) {
    return { block: true, reason: stderr.split("\n")[0] || "Blocked by an ECC hook" };
  }

  const hookOutput = parseHookSpecificOutput(stdout);
  if (hookOutput) {
    if (hookOutput.permissionDecision === "deny") {
      return {
        block: true,
        reason: String(hookOutput.permissionDecisionReason || "Denied by an ECC hook"),
      };
    }
    const context = hookOutput.additionalContext;
    if (typeof context === "string" && context.trim()) {
      return { advisory: context.trim() };
    }
  }

  if (stderr) return { advisory: stderr };
  return {};
}

function parseHookSpecificOutput(stdout: string): Record<string, unknown> | null {
  if (!stdout.startsWith("{")) return null;
  try {
    const parsed = JSON.parse(stdout);
    const section = parsed?.hookSpecificOutput;
    return (section && typeof section === "object") ? section : null;
  } catch {
    return null;
  }
}
