/**
 * Taste Engine Bridge Extension
 *
 * Bridges Taste-Skill (Premium UI/UX Engineering) anti-slop directives into the Pi Harness.
 * - Injects design principles (GEMINI.md) before each agent turn to enforce premium aesthetics.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";

// restore.py copies this bridge to ~/.pi/agent/extensions/taste-bridge/ and
// patches the harness root into package.json. Resolving the root as
// join(__dirname, "../..") — as this bridge used to — lands on ~/.pi, which has
// no pi-config/, so existsSync() was always false and `enableTasteBridge:
// false` never took effect: GEMINI.md was injected into every turn regardless
// of the config, and the status line's "active" was accidentally correct.
// Every other bridge reads pkg["pi-harness"].root; this one now does too.
function harnessRoot(): string {
  const here = dirname(require.resolve("./package.json"));
  try {
    const pkg = JSON.parse(readFileSync(join(here, "package.json"), "utf-8"));
    if (pkg["pi-harness"]?.root) return pkg["pi-harness"].root;
  } catch {}
  return join(here, "../..");
}

function tasteEnabled(): boolean {
  try {
    const cfgPath = join(harnessRoot(), "pi-config", "harness-config.json");
    if (!existsSync(cfgPath)) return true;
    return JSON.parse(readFileSync(cfgPath, "utf8")).enableTasteBridge !== false;
  } catch {
    return true;
  }
}

export default function (pi: ExtensionAPI) {
  // On session start: report the state the bridge is ACTUALLY in. A status line
  // claiming "active" while the injection is disabled is worse than no status —
  // it is the reason a disabled bridge looks like a working one.
  pi.on("session_start", async (_event, ctx) => {
    if (!tasteEnabled()) return;
    ctx.ui.setStatus("taste", "[Taste-Engine] anti-slop design guidelines active");
  });

  // Before each agent turn: inject premium aesthetics guidelines into system prompt
  pi.on("before_agent_start", (event, _ctx) => {
    if (!tasteEnabled()) return; // slim mode: saves ~1,800 chars every turn

    const guidelinesPath = join(dirname(require.resolve("./package.json")), "GEMINI.md");
    if (!existsSync(guidelinesPath)) return;

    try {
      const guidelines = readFileSync(guidelinesPath, "utf8");
      return {
        systemPrompt: (event.systemPrompt ?? "") + "\n\n" + `[Taste-Engine] PREMIUM UI/UX GUIDELINES:\n${guidelines}`,
      };
    } catch {
      return;
    }
  });
}
