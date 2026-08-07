/**
 * The harness works out the next step, instead of hoping the model proposes one.
 *
 * Ten rounds of discussion converged on one sentence: code can decide *how* a
 * task is worked and cannot decide *whether* to start. Promoting
 * `case-framework` into the tier that carries descriptions was the last attempt
 * at the second half, and it was measured at 0/3 loads on a three-deliverable
 * brief.
 *
 * The 2026 literature names the two modes. Agent-proposed activation puts a
 * skill in front of the model and waits. Policy-mediated activation has the
 * system decide from configuration and triggers. Anthropic's guidance is
 * blunter: a deterministic backbone owns the flow, the model fills specific
 * steps.
 *
 * Pi has the backbone parts, and this repo already uses them — `sendMessage`
 * with `followUp` and `triggerTurn` is how async-exec wakes the agent. Verified
 * in a real session (019fcf32) before any of this was written:
 *
 *      8  ASSISTANT  text                       turn ended
 *      9  CUSTOM     universal-tag-transformer  injected
 *     10  ASSISTANT  bash                       a new turn, with a real call
 *
 * No user message between 8 and 10. The mechanism advances a turn; it had only
 * ever been used to correct one.
 *
 * The next step is looked up, never invented. Every row points at a clause of
 * `external/Local-Agent-Workspace/references/for_agents.md`, and every
 * condition is file existence. Nothing here judges content — this repo has
 * learned twice that demanding quality produces fabrication.
 *
 * What this does not fix, stated plainly: the instruction is still text, and
 * the model can still ignore it. What changes is the shape of the failure. A
 * model that quietly never starts is invisible; a model that ignores an
 * injected step leaves the queue in the same state, so the same step arrives
 * again — and a failure that repeats is a failure that can be counted.
 */

import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const TASK_DIR_RE = /^Task_(\d+)_/;

/** Below this, `output.md` is a placeholder rather than a deliverable. */
export const OUTPUT_MIN_CHARS = 200;

/** How many times one step may be injected before the run is escalated. */
export const MAX_ADVANCES_PER_STEP = 3;

const OPEN_STATES = new Set(["IN_PROGRESS", "REVIEW"]);

export interface NextStep {
  task: string;
  status: string;
  /** "" when nothing is missing and the step is a transition. */
  missing: "" | "planning" | "self-review" | "output" | "retro";
  instruction: string;
  /**
   * The protocol's stopping point: nothing this session may do next.
   *
   * loopy states it plainly — a loop is a feedback system with terminal states,
   * not permission for endless autonomy. Without this flag the handoff step was
   * re-issued and then escalated as stuck, because it is a state that by design
   * never changes.
   */
  terminal?: true;
}

export interface Advance {
  message: string;
  /**
   * The advancer has given up on this step and paused ITSELF.
   *
   * Not `escalate`. The previous version asked the model to write ESCALATED
   * into `status.txt`, so every time the automation quit, the protocol recorded
   * a failed task: three of five measured runs ended ESCALATED and at least two
   * of those tasks were progressing fine. `reference/pi-until-done` pauses its
   * own state and never touches the executed task
   * (`hooks/agent-end-helpers.ts:13`); that is the shape adopted here.
   */
  paused?: true;
}

/**
 * What a tool call is worth as evidence that the cycle did something.
 *
 * Borrowed wholesale from pi-until-done (`hooks/tools.ts:65`) — these are its
 * numbers, not ones this project derived, and that is recorded so a later
 * measurement can question them. A stall is a cycle that scores zero, not a
 * cycle that failed to move the state: a step can legitimately take several
 * cycles of reading and editing.
 */
const PROGRESS_WEIGHTS: Record<string, number> = {
  write: 3, edit: 3, bash: 2, read: 1, grep: 1, find: 1, ls: 1,
};
const DEFAULT_WEIGHT = 2;

/** Cycles scoring zero before the advancer pauses itself. */
export const MAX_IDLE_CYCLES = 3;

function read(path: string): string | null {
  try {
    return readFileSync(path, "utf8");
  } catch {
    return null;
  }
}

function taskDirs(queueDir: string): Array<{ index: number; name: string; status: string }> {
  let names: string[];
  try {
    if (!statSync(queueDir).isDirectory()) return [];
    names = readdirSync(queueDir);
  } catch {
    return [];
  }
  const out: Array<{ index: number; name: string; status: string }> = [];
  for (const name of names.sort()) {
    const m = TASK_DIR_RE.exec(name);
    if (!m) continue;
    const status = (read(join(queueDir, name, "status.txt")) || "").trim();
    if (!status) continue;
    out.push({ index: parseInt(m[1], 10), name, status });
  }
  return out;
}

/**
 * The task the next step belongs to.
 *
 * An open task wins over a pending one. Two open tasks yield nothing: the queue
 * guard already refuses that state, and advancing on a guess would file the
 * next step against the wrong task.
 */
function currentTask(queueDir: string): { name: string; status: string } | null {
  const tasks = taskDirs(queueDir);
  const open = tasks.filter((t) => OPEN_STATES.has(t.status));
  if (open.length > 1) return null;
  if (open.length === 1) return { name: open[0].name, status: open[0].status };
  const pending = tasks.filter((t) => t.status === "PENDING").sort((a, b) => a.index - b.index);
  if (!pending.length) return null;
  return { name: pending[0].name, status: pending[0].status };
}

/**
 * The next step for a queue, or null.
 *
 * Pure: reads files, decides nothing else. The table below is the whole of it.
 */
export function nextStep(queueDir: unknown): NextStep | null {
  if (typeof queueDir !== "string" || !queueDir) return null;
  let task: { name: string; status: string } | null;
  try {
    task = currentTask(queueDir);
  } catch {
    return null;
  }
  if (!task) return null;

  const dir = join(queueDir, task.name);
  const at = (f: string) => join(dir, f);
  const say = (missing: NextStep["missing"], instruction: string,
               terminal?: true): NextStep =>
    ({ task: task!.name, status: task!.status, missing, instruction,
       ...(terminal ? { terminal } : {}) });

  // §6 step 1 — a pending task begins by claiming itself.
  if (task.status === "PENDING") {
    return say("", `[C.A.S.E.] 下一步:把 ${task.name}/status.txt 改成 IN_PROGRESS,開始這一項。` +
      `(for_agents.md §6 step 1)`);
  }

  if (task.status === "IN_PROGRESS") {
    const planning = read(at("planning.md"));
    // §6 step 4 — a plan, and a self-review of that plan, before any work.
    if (planning === null) {
      return say("planning",
        `[C.A.S.E.] 下一步:替 ${task.name} 寫 planning.md —— 具體步驟、要動的檔案、` +
        `測試策略,並附 "## Self-Review" 段落對照 recipe.md 的 Local DoD 逐項自審。` +
        `(for_agents.md §6 step 4)`);
    }
    if (!planning.includes("## Self-Review")) {
      return say("self-review",
        `[C.A.S.E.] 下一步:${task.name}/planning.md 缺 "## Self-Review"。` +
        `逐項對照 recipe.md 的 Local DoD:每一條有沒有對應步驟?有沒有步驟牴觸 Constraints?` +
        `有沒有建立在 recipe/role 不支持的假設上?(for_agents.md §6 step 4)`);
    }
    // §6 step 8 — the deliverable itself.
    const output = read(at("output.md"));
    if (output === null || output.trim().length < OUTPUT_MIN_CHARS) {
      return say("output",
        `[C.A.S.E.] 下一步:把 ${task.name} 的成果寫進 output.md,對照 recipe.md 的 ` +
        `Local Definition of Done 逐條交代。(for_agents.md §6 step 8)`);
    }
    // §6 step 9 — hand it over.
    return say("",
      `[C.A.S.E.] 下一步:${task.name} 的計畫與產出都在了,把 status.txt 改成 REVIEW 送審。` +
      `(for_agents.md §6 step 9)`);
  }

  if (task.status === "REVIEW") {
    // §13a — the retrospective is mandatory before DONE.
    if (!existsSync(at("retro.md"))) {
      return say("retro",
        `[C.A.S.E.] 下一步:替 ${task.name} 寫 retro.md,四段缺一不可 —— ` +
        `"## Gaps & Missteps"、"## Optimization Opportunities"、"## Lessons Learned"、` +
        `"## Feedback to CASE"。(for_agents.md §13a)`);
    }
    // §1 is non-negotiable and Path B still requires a fresh context, so this
    // session is not allowed to approve its own work. The step is to stop.
    return say("",
      `[C.A.S.E.] ${task.name} 已在 REVIEW 且復盤已寫。核可必須由**另一個 session** 進行 —— ` +
      `§1 的雙軌驗證不可協商,Path B 的自主核可也明訂需要 fresh context。` +
      `這一輪到此為止,請告訴使用者可以開新 session 當 Checker。`, true);
  }

  // DONE / ESCALATED / anything unrecognised: not this mechanism's business.
  return null;
}

export class QueueAdvancer {
  private seen = new Map<string, number>();
  private done = new Set<string>();
  private progress = 0;
  private idleCycles = 0;

  /** Score a tool call for this cycle. Called from `tool_call`. */
  noteProgress(toolName: unknown): void {
    const name = String(toolName ?? "");
    if (!name) return;
    this.progress += PROGRESS_WEIGHTS[name] ?? DEFAULT_WEIGHT;
  }

  /** This cycle's weighted score, for tests and for the status line. */
  progressThisCycle(): number {
    return this.progress;
  }

  /**
   * End of one agent run.
   *
   * A cycle is `agent_settled` to `agent_settled`, not turn to turn. Probed
   * 2026-08-06: `agent_settled` fires once per agent run, 1ms after
   * `agent_end`, while `turn_end` fires on every turn — and counting turns is
   * what declared steps in normal progress stuck.
   */
  endCycle(): void {
    if (this.progress === 0) this.idleCycles += 1;
    else this.idleCycles = 0;
    this.progress = 0;
  }

  /**
   * The message to inject, or null.
   *
   * Returns `escalate` once a step has been injected its full budget without
   * the queue moving, and then stays silent. Repeating an instruction the run
   * has already ignored three times is a loop with extra steps — the same
   * reasoning, and the same budget, as every other guard in this harness.
   */
  advance(queueDir: unknown): Advance | null {
    let step: NextStep | null;
    try {
      step = nextStep(queueDir);
    } catch {
      return null;
    }
    if (!step) return null;

    const key = `${step.task}:${step.status}:${step.missing}`;
    if (this.done.has(key)) return null;

    // A terminal step is the protocol's stopping point, not a stalled one.
    // "Approval belongs to another session" is correct and stable, and the old
    // counter escalated it as stuck — reproduced deterministically before this
    // change. Say it once; then stop.
    if (step.terminal) {
      this.done.add(key);
      return { message: step.instruction };
    }

    // Idleness, not repetition, is what retires it. A cycle that called tools
    // was working even if the state has not moved yet.
    if (this.idleCycles >= MAX_IDLE_CYCLES) {
      this.done.add(key);
      return {
        paused: true,
        message:
          `[C.A.S.E.] 推進器已暫停:連續 ${MAX_IDLE_CYCLES} 個回合完全沒有工具呼叫,` +
          `所以它停止推進 ${step.task} 的「${step.missing || "下一步"}」。` +
          `**任務狀態沒有被更動,也不需要被更動** —— 停下來的是自動化,不是這件工作。` +
          `需要繼續時直接告訴我下一步,或自行接手。`,
      };
    }

    this.seen.set(key, (this.seen.get(key) ?? 0) + 1);
    return { message: step.instruction };
  }

  /** A new session starts with no history. */
  reset(): void {
    this.seen.clear();
    this.done.clear();
    this.progress = 0;
    this.idleCycles = 0;
  }
}
