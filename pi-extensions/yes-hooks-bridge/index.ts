/**
 * Safety Hooks Bridge Extension (folder: yes-hooks-bridge)
 *
 * Hosts two deterministic tool_call guards the model CANNOT ignore — the whole
 * point of a hook over a text rule, and especially valuable with weak/uncensored
 * local models that drift past AGENTS.md prose under load:
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

export default function (pi: ExtensionAPI) {
  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName === "bash") return bashGuard(event, ctx);
    if (event.toolName === "write" || event.toolName === "edit") return containmentGuard(event, ctx);
  });
}
