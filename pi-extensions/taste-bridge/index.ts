/**
 * Taste Engine Bridge Extension
 *
 * Bridges Taste-Skill (Premium UI/UX Engineering) anti-slop directives into the Pi Harness.
 * - Injects design principles (GEMINI.md) before each agent turn to enforce premium aesthetics.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

// Two stacked defects made this bridge a no-op that looked alive:
//
//  1. This package.json declares "type": "module", so Pi loads the bridge as
//     ESM, where `require` does not exist. Every call to
//     `require.resolve("./package.json")` threw. The engine catches handler
//     errors and reports them to the TUI, so under --print the failure was
//     completely invisible — before_agent_start never completed once.
//  2. Even reaching the config read, the root was resolved as
//     join(__dirname, "../..") — under the installed layout that is ~/.pi,
//     which holds no pi-config/, so `enableTasteBridge: false` could not have
//     taken effect either.
//
// Proven by importing the installed copy directly:
//     handler THREW: require is not defined
// Fix: import.meta.url (the ESM equivalent, as skill-namespace-guard uses) plus
// the pkg["pi-harness"].root that restore.py patches in, like every other bridge.
const HERE = dirname(fileURLToPath(import.meta.url));

function harnessRoot(): string {
  try {
    const pkg = JSON.parse(readFileSync(join(HERE, "package.json"), "utf-8"));
    if (pkg["pi-harness"]?.root) return pkg["pi-harness"].root;
  } catch {}
  return join(HERE, "../..");
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

    const guidelinesPath = join(HERE, "GEMINI.md");
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
