/**
 * Taste Engine Bridge Extension
 *
 * Bridges Taste-Skill (Premium UI/UX Engineering) anti-slop directives into the Pi Harness.
 * - Injects design principles (GEMINI.md) before each agent turn to enforce premium aesthetics.
 */
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";

export default function (pi: ExtensionAPI) {
  // On session start: show status
  pi.on("session_start", async (_event, ctx) => {
    ctx.ui.setStatus("taste", "[Taste-Engine] anti-slop design guidelines active");
  });

  // Before each agent turn: inject premium aesthetics guidelines into system prompt
  pi.on("before_agent_start", (_event, _ctx) => {
    const __dirname = dirname(require.resolve("./package.json"));
    const guidelinesPath = join(__dirname, "GEMINI.md");

    if (!existsSync(guidelinesPath)) return;

    try {
      const guidelines = readFileSync(guidelinesPath, "utf8");
      return {
        systemPrompt: `[Taste-Engine] PREMIUM UI/UX GUIDELINES:\n${guidelines}`,
      };
    } catch {
      return;
    }
  });
}
