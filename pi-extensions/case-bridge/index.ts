/**
 * C.A.S.E. Framework Bridge Extension
 *
 * Bridges C.A.S.E. protocol rules and context into pi's event system.
 * - Injects Constitution (00_Constitution/core.md) and Roadmap (01_Roadmap/roadmap.md)
 * - Injects absolute path references for bootstrap.py and verifiers
 * - Logs C.A.S.E. framework status on session_start
 */
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";

const MAX_INJECT_CHARS = 3000;

function fileExists(dir: string, name: string): boolean {
  return existsSync(join(dir, name));
}

function readHead(dir: string, name: string, maxChars?: number): string {
  const path = join(dir, name);
  if (!existsSync(path)) return "";
  try {
    const raw = readFileSync(path, "utf8");
    return maxChars ? raw.slice(0, maxChars) : raw;
  } catch {
    return "";
  }
}

function isCaseProject(cwd: string): boolean {
  return fileExists(cwd, "CASE.md") || fileExists(cwd, "00_Constitution");
}

export default function (pi: ExtensionAPI) {
  // On session start: detect C.A.S.E. status
  pi.on("session_start", async (_event, ctx) => {
    if (!isCaseProject(ctx.cwd)) return;
    ctx.ui.setStatus("case", "[C.A.S.E.] framework active in workspace");
  });

  // Before each agent turn: inject C.A.S.E. rules and file-based state context
  pi.on("before_agent_start", (event, ctx) => {
    // Dynamic path resolution for harness root
    const __dirname = dirname(require.resolve("./package.json"));
    const pkg = JSON.parse(readFileSync(join(__dirname, "package.json"), "utf-8"));
    const HARNESS_ROOT = pkg["pi-harness"]?.root || join(__dirname, "../..");

    const BOOTSTRAP_SCRIPT = join(HARNESS_ROOT, "external/Local-Agent-Workspace/scripts/bootstrap.py").replace(/\\/g, "/");
    const VERIFIER_SCRIPT = join(HARNESS_ROOT, "external/Local-Agent-Workspace/verifiers/verify.py").replace(/\\/g, "/");

    const parts: string[] = [
      `[C.A.S.E.] C.A.S.E. (Constitution-Architecture-State-Execution) framework is active in this harness.`,
      `- To bootstrap C.A.S.E. in a project, run: python "${BOOTSTRAP_SCRIPT}" .`,
      `- To verify a C.A.S.E. task queue folder, run: python "${VERIFIER_SCRIPT}" <path_to_task_folder>`
    ];

    if (isCaseProject(ctx.cwd)) {
      const constitution = readHead(join(ctx.cwd, "00_Constitution"), "core.md", MAX_INJECT_CHARS);
      const roadmap = readHead(join(ctx.cwd, "01_Roadmap"), "roadmap.md", MAX_INJECT_CHARS);

      if (constitution.trim()) {
        parts.push(
          "",
          "---BEGIN C.A.S.E. CONSTITUTION---",
          constitution.trim(),
          "---END C.A.S.E. CONSTITUTION---"
        );
      }
      if (roadmap.trim()) {
        parts.push(
          "",
          "---BEGIN C.A.S.E. ROADMAP---",
          roadmap.trim(),
          "---END C.A.S.E. ROADMAP---"
        );
      }
    }

    return {
      systemPrompt: (event.systemPrompt ?? "") + "\n\n" + parts.join("\n"),
    };
  });
}
