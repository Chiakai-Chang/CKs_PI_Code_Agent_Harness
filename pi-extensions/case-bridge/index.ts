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

import { TaskQueueGuard } from "./task-queue-guard.ts";
import { ActionLogger } from "./action-log.ts";
import { QueueAdvancer } from "./queue-advancer.ts";
import { PhaseGate, useScopeSnapshot } from "./phase-gate.ts";
import { ScopeSnapshot } from "./harness-scope.ts";
import { PhaseNotice } from "./phase-notice.ts";

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
/**
 * Fails CLOSED, unlike `caseBridgeEnabled`.
 *
 * The bridge only injects text; the advancer triggers a turn, which is a larger
 * behaviour change than any refusal in this harness. GateGuard is the standing
 * lesson: a mechanism nobody had run went live and denied the first bash command
 * of every session. Whether this default flips is for measurement to decide,
 * not for the design.
 */
function harnessRoot(): string | null {
  try {
    const here = dirname(require.resolve("./package.json"));
    const pkg = JSON.parse(readFileSync(join(here, "package.json"), "utf-8"));
    return pkg["pi-harness"]?.root || join(here, "../..");
  } catch {
    return null;
  }
}

/**
 * Fails CLOSED, and now resolves per project.
 *
 * A project may switch this on for itself with `.pi-harness.json`; without one
 * the global file decides exactly as before. Measuring used to require flipping
 * the global flag, which drove every other C.A.S.E. project the user had open
 * for the duration — see harness-scope.ts.
 */
const scope = new ScopeSnapshot();

function caseAdvancerEnabled(_harnessRoot: string, _cwd?: string): boolean {
  // The session's snapshot, not the file. Editing `.pi-harness.json` mid-run
  // used to change behaviour immediately and left nothing in the record saying
  // which configuration a run had used — and three measurement rounds this
  // week were already invalidated by the environment rather than the harness.
  try {
    return scope.get("enableCaseAdvancer") === true;
  } catch {
    return false;
  }
}

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

/** The assistant text of a turn, if it said anything at all. */
function extractText(message: unknown): string {
  const content = (message as { content?: unknown } | undefined)?.content;
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";
  return content.map((b) => (b as { type?: string; text?: string })?.type === "text"
    ? (b as { text?: string }).text ?? "" : "").join(" ");
}

export default function (pi: ExtensionAPI) {
  // The half of the protocol that is a transition rather than a decision. See
  // task-queue-guard.ts — every status change is a write, a write is a
  // tool_call, and tool_call fires before the tool runs, so the old value is
  // still there to compare against.
  //
  // Measured the day this landed: the same protocol as skill text was skipped
  // 3/3, and `case-framework` promoted into the core tier with a full
  // description was loaded 0/3. A refusal is the one channel that has moved
  // behaviour in this harness.
  const queueGuard = new TaskQueueGuard();

  // The audit trail, written here rather than requested from the model. Asking
  // the agent under audit to keep its own audit trail is worth what it was
  // measured to be worth: session 019fd29d made 40 tool calls and wrote nothing.
  const actionLog = new ActionLogger();

  // The backbone. Ten rounds established that code cannot decide whether to
  // start, only how to proceed — so this stops asking the model to propose the
  // next step and works it out from the queue on disk. Default off; see
  // caseAdvancerEnabled.
  const advancer = new QueueAdvancer();

  // On session start: detect C.A.S.E. status
  pi.on("session_start", async (_event, ctx) => {
    // A new session is a new Worker: whoever moved a task to IN_PROGRESS last
    // time is not this session, and the dual-track rule must not carry over.
    // A session boundary is where the configuration is read, once.
    scope.take(ctx.cwd, harnessRoot() ?? "");
    useScopeSnapshot(scope);
    queueGuard.reset();
    queueGuard.humanApproved.reset();
    phaseNotice.reset();
    advancer.reset();
    if (!isCaseProject(ctx.cwd)) return;
    if (!caseBridgeEnabled()) return;
    ctx.ui.setStatus("case", "[C.A.S.E.] framework active in workspace");
  });

  // Deliberately not gated on isCaseProject(cwd): a project with
  // 02_Task_Queue/Task_NNN_*/ is working the protocol whether or not it also
  // has CASE.md at the root, and the guard's own scope is already narrow enough
  // that nothing else in any project can reach it.
  // "Plan first" made unavailable rather than advised. The research-shaped run
  // opened with six searches and three page opens before any injection landed,
  // and its task never left PENDING — a mechanism speaking at `turn_end` cannot
  // catch that, which is what the same measurement concluded.
  const phaseGate = new PhaseGate();
  const phaseNotice = new PhaseNotice();

  // Path A's evidence, taken from what the user actually typed. The type
  // declares `prompt` as "the raw user prompt text (after expansion)", so this
  // is the bridge seeing the person speak rather than the model reporting that
  // they did — a distinction `blocked-claim` had to be built to enforce once
  // already.
  pi.on("before_agent_start", async (event) => {
    if (!caseBridgeEnabled()) return;
    const prompt = (event as { prompt?: unknown }).prompt;
    queueGuard.humanApproved.note(prompt);

    // A duplicate classifier lived here for one commit. `task-shape-bridge`
    // already classified request shape at this same event, in any project, and
    // already injected a routing note — it had simply never fired on Chinese
    // prompts because its separator set lacked the fullwidth comma. Prior Art
    // First applied to our own repository, and I skipped it.
  });

  pi.on("tool_call", async (event, ctx) => {
    if (!caseBridgeEnabled()) return;
    // Order matters: the transition guard's complaint is the more specific one,
    // so it speaks first when both would refuse the same call.
    const refusal = queueGuard.check(event.toolName, event.input, ctx.cwd);
    if (refusal) {
      ctx.ui.notify("🔒 C.A.S.E. 佇列規則:已擋下不合協定的狀態變更", "warning");
      return refusal;
    }
    // Evidence that this cycle did something. Weighted, and counted here
    // because `tool_call` fires whether or not the call is later refused.
    advancer.noteProgress(event.toolName);
    const phase = phaseGate.check(join(ctx.cwd ?? "", "02_Task_Queue"), event.toolName, event.input);
    if (phase) {
      ctx.ui.notify("🚦 C.A.S.E. 階段閘:先認領、先規劃,再產出", "warning");
      return phase;
    }
  });

  // After a call runs. `tool_result` rather than `tool_call` on purpose: a
  // refused call never executed, and an audit trail that records intentions is
  // not an audit trail. Returns nothing, so the tool result is untouched.
  pi.on("tool_result", async (event, ctx) => {
    if (!caseBridgeEnabled()) return;
    actionLog.record(ctx.cwd, event.toolName, event.input, event.isError === true);
    // Say when the door opened. The gate closing it was the only thing the
    // model ever heard: twenty refusals, zero permissions, and it stopped
    // searching for the rest of the run (4b, 2026-08-08). This rides the
    // result of the claim itself — the moment the statement becomes true, on
    // one of the two channels measured to reach the model. Appended, never
    // replacing: a handler returning a bare block was dropped in silence once
    // while eleven tests stayed green.
    const opened = phaseNotice.afterToolResult(
      join(ctx.cwd ?? "", "02_Task_Queue"), event.toolName, event.input,
      event.isError === true);
    if (opened) {
      return { content: [...(event.content ?? []), { type: "text", text: opened }] };
    }
  });

  // At the end of a turn: work out the next step and drive it.
  //
  // `followUp` + `triggerTurn` is the only delivery that advances a turn rather
  // than waiting for a human — verified in session 019fcf32, where a custom
  // message sat between an assistant turn that ended in text and a new
  // assistant turn that made a real tool call, with no user message between.
  // `turn_end`, and this is a REVERSAL recorded rather than hidden.
  //
  // The port from `reference/pi-until-done` moved this to `agent_settled`, and
  // the move failed for a reason its own type declaration states outright:
  // "Fired after an agent run has fully settled and no automatic retry,
  // compaction, or queued continuation will run." A continuation queued there
  // is by definition too late. Measured twice: the injection never reached the
  // session. `sendUserMessage` — what pi-until-done uses — hung the process in
  // `--print` on both attempts, ten minutes with no session file.
  //
  // `turn_end` + sendMessage(followUp, triggerTurn) is the one channel measured
  // to deliver here: eleven injections in the clean rerun. Delivery was never
  // the defect. Speaking on EVERY turn was, and writing the automation's
  // surrender into the task's status was. Those two are fixed below and in
  // queue-advancer.ts, without changing a channel that works.
  //
  // So the advancer speaks only when a turn produced text and called nothing:
  // the model has stopped and is talking, which is exactly when a push is due.
  // A tool-only turn is not the end of a reply, and mid-work is not a stall.
  pi.on("turn_end", async (event, ctx) => {
    // The gate's budget advances per turn, not per call: this model issues
    // five parallel tool calls at once, and a call-counted budget was spent
    // inside the first batch before one refusal reached it (measured
    // 2026-08-08). This runs before every early return below — a gate whose
    // budget never advances is a wall with no door.
    phaseGate.turnEnded();

    const root = harnessRoot();
    if (!root || !caseAdvancerEnabled(root, ctx.cwd)) return;
    if (!isCaseProject(ctx.cwd)) return;

    const spoke = Boolean(extractText((event as { message?: unknown }).message).trim());
    const worked = advancer.progressThisCycle() > 0;
    advancer.endCycle();
    if (!spoke || worked) return;

    const step = advancer.advance(join(ctx.cwd, "02_Task_Queue"));
    if (!step) return;
    if (step.paused) {
      ctx.ui.notify("⏸️ C.A.S.E. 推進器已暫停(任務狀態未變更)", "warning");
      pi.sendMessage(
        { customType: "case-advance-paused", content: step.message, display: true },
        { deliverAs: "nextTurn" },
      );
      return;
    }
    ctx.ui.notify("▶️ C.A.S.E. 推進下一步", "info");
    pi.sendMessage(
      { customType: "case-advance", content: step.message, display: true },
      { deliverAs: "followUp", triggerTurn: true },
    );
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
