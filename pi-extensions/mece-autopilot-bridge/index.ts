/**
 * MECE-Autopilot Bridge Extension
 *
 * Bridges MECE-Autopilot reasoning engine into the Pi Harness.
 * - Injects absolute path references for mece-autopilot-orchestrator.js
 * - Logs MECE-Autopilot status on session_start
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { buildNotice } from "./notice.ts";


// import.meta.url, not require.resolve: Pi's loader shims `require`, but bare
// node does not, and the `catch` around every config read here then returns the
// DEFAULT — so each switch reported ON regardless of harness-config.json in any
// runtime that is not Pi. That invalidated the first A/B run on 2026-08-16 (both
// arms identical) and is enforced from 2026-08-16 by tests/test_bridge_config_readers.py.
function moduleSelfPath(): string {
  return join(dirname(fileURLToPath(import.meta.url)), "package.json");
}

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
    const __dirname = dirname(moduleSelfPath());
    const pkg = JSON.parse(readFileSync(join(__dirname, "package.json"), "utf-8"));
    const HARNESS_ROOT = pkg["pi-harness"]?.root || join(__dirname, "../..");

    const ORCHESTRATOR_SCRIPT = join(HARNESS_ROOT, "external/mece-autopilot/scripts/mece-autopilot-orchestrator.js").replace(/\\/g, "/");

    const parts: string[] = buildNotice(ORCHESTRATOR_SCRIPT);

    return {
      systemPrompt: (event.systemPrompt ?? "") + "\n\n" + parts.join("\n"),
    };
  });
}
