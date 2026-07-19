/**
 * YES.md Hooks Bridge Extension
 *
 * Wires YES.md's `pre-bash-guard.sh` into Pi as a real, deterministic block on
 * destructive shell commands (rm -rf /, git push --force, DROP TABLE, mkfs,
 * fork bombs, …). This is enforcement the model cannot ignore — the point of a
 * hook over a text rule, and especially valuable with uncensored local models.
 *
 * Scope is deliberately narrow (MECE decision): ONLY the destructive-command
 * blocker is wired. YES.md's post-edit / post-deploy hooks are reminders that
 * duplicate AGENTS.md §9 and only add noise, so they are intentionally skipped.
 * The behavioral discipline half of YES.md ships as the `yes` skill, not here.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
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

export default function (pi: ExtensionAPI) {
  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName !== "bash") return;
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
  });
}
