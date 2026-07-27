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

// restore.py copies this bridge to ~/.pi/agent/extensions/taste-bridge/ and
// patches the harness root into its package.json. This bridge alone ignored
// that and resolved the root as join(__dirname, "../.."), which under the
// installed layout is ~/.pi — a directory with no pi-config/. existsSync() was
// therefore always false, the config read never fired, and
// `enableTasteBridge: false` did nothing: GEMINI.md was appended to the system
// prompt on every turn regardless of configuration.
//
// Measured with a probe extension loaded last, so it sees the fully chained
// prompt:  taste ON 97,319 chars / OFF 95,559 chars (delta 1,760 = the injection).
//
// import.meta.url rather than require.resolve: Pi's loader does provide a
// `require` shim to bridges (verified under Pi for both "type": "module" and
// CJS-declared packages), but bare `node` does not when the file is imported as
// ESM — and importing the installed copy in node is how these handlers get
// behaviourally tested.
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
