/**
 * C.A.S.E. Framework Bridge Extension
 *
 * Bridges C.A.S.E. protocol rules and context into pi's event system.
 * - Injects Constitution (00_Constitution/core.md) and Roadmap (01_Roadmap/roadmap.md)
 * - Injects absolute path references for bootstrap.py and verifiers
 * - Logs C.A.S.E. framework status on session_start
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
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

// Mirrors the enableCaseBridge check in before_agent_start. A status line that
// says "active" while the injection is switched off is how a disabled bridge
// passes for a working one (taste-bridge shipped that way for months).
function caseBridgeEnabled(): boolean {
  try {
    const here = dirname(require.resolve("./package.json"));
    const pkg = JSON.parse(readFileSync(join(here, "package.json"), "utf-8"));
    const root = pkg["pi-harness"]?.root || join(here, "../..");
    const cfgPath = join(root, "pi-config", "harness-config.json");
    if (!existsSync(cfgPath)) return true;
    return JSON.parse(readFileSync(cfgPath, "utf8")).enableCaseBridge !== false;
  } catch {
    return true;
  }
}

export default function (pi: ExtensionAPI) {
  // On session start: detect C.A.S.E. status
  pi.on("session_start", async (_event, ctx) => {
    if (!isCaseProject(ctx.cwd)) return;
    if (!caseBridgeEnabled()) return;
    ctx.ui.setStatus("case", "[C.A.S.E.] framework active in workspace");
  });

  // Before each agent turn: inject C.A.S.E. rules and file-based state context
  pi.on("before_agent_start", (event, ctx) => {
    // Dynamic path resolution for harness root
    const __dirname = dirname(require.resolve("./package.json"));
    const pkg = JSON.parse(readFileSync(join(__dirname, "package.json"), "utf-8"));
    const HARNESS_ROOT = pkg["pi-harness"]?.root || join(__dirname, "../..");

    let isSlim = false;
    let maxChars = MAX_INJECT_CHARS;

    try {
      const cfgPath = join(HARNESS_ROOT, "pi-config", "harness-config.json");
      if (existsSync(cfgPath)) {
        const cfg = JSON.parse(readFileSync(cfgPath, "utf8"));
        if (cfg.enableCaseBridge === false) return;
        if (cfg.promptProfile === "slim") {
          isSlim = true;
          maxChars = cfg.caseBridgeMaxChars || 600;
        }
      }
    } catch {}

    const BOOTSTRAP_SCRIPT = join(HARNESS_ROOT, "external/Local-Agent-Workspace/scripts/bootstrap.py").replace(/\\/g, "/");
    const VERIFIER_SCRIPT = join(HARNESS_ROOT, "external/Local-Agent-Workspace/verifiers/verify.py").replace(/\\/g, "/");

    const parts: string[] = [
      `[C.A.S.E.] C.A.S.E. (Constitution-Architecture-State-Execution) framework is active in this harness.`
    ];

    if (!isSlim) {
      parts.push(
        `- To bootstrap C.A.S.E. in a project, run: python "${BOOTSTRAP_SCRIPT}" .`,
        // The old wording said "task queue folder" and then passed a task
        // folder. Both now exist and check different things: one task package,
        // or the invariant the queue is for — at most one task IN_PROGRESS.
        // `--strict` matters because ten of the verifier's fifteen checks are
        // warnings by default, so a task with no audit trail and no Definition
        // of Done still exits 0.
        `- To verify one C.A.S.E. task package, run: python "${VERIFIER_SCRIPT}" <path_to_task_folder> --strict`,
        `- To verify the queue itself (at most one task IN_PROGRESS, tasks finished in order), run: python "${VERIFIER_SCRIPT}" --queue <path_to_02_Task_Queue>`
      );
    }

    if (isCaseProject(ctx.cwd)) {
      const constitution = readHead(join(ctx.cwd, "00_Constitution"), "core.md", maxChars);
      const roadmap = readHead(join(ctx.cwd, "01_Roadmap"), "roadmap.md", maxChars);
      const addendum = isSlim ? "" : readHead(join(HARNESS_ROOT, "pi-rules"), "case-autonomous-execution.md", maxChars);

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
      if (addendum.trim()) {
        parts.push(
          "",
          "---BEGIN C.A.S.E. HARNESS ADDENDUM---",
          addendum.trim(),
          "---END C.A.S.E. HARNESS ADDENDUM---"
        );
      }
    }

    return {
      systemPrompt: (event.systemPrompt ?? "") + "\n\n" + parts.join("\n"),
    };
  });
}
