/**
 * MECE-Autopilot Bridge Extension
 *
 * Bridges MECE-Autopilot reasoning engine into the Pi Harness.
 * - Injects absolute path references for mece-autopilot-orchestrator.js
 * - Logs MECE-Autopilot status on session_start
 */
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";

function fileExists(dir: string, name: string): boolean {
  return existsSync(join(dir, name));
}

function hasActiveSession(cwd: string): boolean {
  return fileExists(cwd, "wiki/.mece_state.json");
}

export default function (pi: ExtensionAPI) {
  // On session start: detect MECE-Autopilot status
  pi.on("session_start", async (_event, ctx) => {
    if (!hasActiveSession(ctx.cwd)) return;
    ctx.ui.setStatus("mece-autopilot", "[MECE-Autopilot] active session in workspace");
  });

  // Before each agent turn: inject MECE-Autopilot absolute paths and guidance
  pi.on("before_agent_start", (event, _ctx) => {
    // Dynamic path resolution for harness root
    const __dirname = dirname(require.resolve("./package.json"));
    const pkg = JSON.parse(readFileSync(join(__dirname, "package.json"), "utf-8"));
    const HARNESS_ROOT = pkg["pi-harness"]?.root || join(__dirname, "../..");

    const ORCHESTRATOR_SCRIPT = join(HARNESS_ROOT, "external/mece-autopilot/scripts/mece-autopilot-orchestrator.js").replace(/\\/g, "/");

    const parts: string[] = [
      `[MECE-Autopilot] MECE-Autopilot reasoning engine is available in this harness.`,
      `- To initialize a new MECE roundtable discussion for a decision: node "${ORCHESTRATOR_SCRIPT}" --init "<problem_description>"`,
      `- To verify current step and progress to next expert/round: node "${ORCHESTRATOR_SCRIPT}" --step`,
      `- To view current discussion status: node "${ORCHESTRATOR_SCRIPT}" --status`,
      `- To reset state: node "${ORCHESTRATOR_SCRIPT}" --reset`,
      `If MECE-Autopilot is active (check if wiki/.mece_state.json exists), follow the active instructions in wiki/next_task.md.`
    ];

    return {
      systemPrompt: (event.systemPrompt ?? "") + "\n\n" + parts.join("\n"),
    };
  });
}
