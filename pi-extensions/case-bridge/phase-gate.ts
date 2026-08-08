/**
 * "Plan first" enforced where it can be enforced: at `tool_call`.
 *
 * The owner's complaint was that Pi starts searching immediately and produces a
 * conclusion, with Superpowers, C.A.S.E. and planning-with-files installed and
 * unused. The correction that shapes this file: "他多搜幾次是好的阿?越多越好不是?
 * 我抱怨的是他沒有先規劃就開始." So searching is not the target. Starting without
 * claiming and planning is.
 *
 * Measured 2026-08-06 in the research-shaped run: the first eleven actions were
 * six searches and three page opens; the first advancer injection arrived after
 * them; the task's status never left PENDING. That measurement's own verdict
 * says a mechanism speaking at `turn_end` cannot catch a turn that already
 * searched — only `tool_call` can.
 *
 * `research/auto-pi` has this implemented (`extensions/loop.ts:1020`): a phase
 * tool allowlist refused at `tool_call`, PLAN read-only. Adopted. Its phase
 * model is not: ours comes from C.A.S.E. protocol state, because a second state
 * machine beside the protocol would fight it.
 *
 *     PENDING, unclaimed        CLAIM  research refused; reads and status.txt fine
 *     IN_PROGRESS, no plan      PLAN   deliverables refused; research WIDE OPEN
 *     otherwise                 open   nothing refused
 *
 * Fails open on anything it does not recognise. A gate that misfires in an
 * unfamiliar project is switched off within a day, and then it guards nothing.
 */

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { bashWriteTargets } from "./task-queue-guard.ts";

/** Tools that reach the network for research. */
const RESEARCH_TOOLS = new Set(["web_search", "web_open", "web_snapshot", "deep_research"]);

/**
 * Files the PLAN phase may still write.
 *
 * An allowlist, not a blocklist of "deliverables". Naming what a deliverable is
 * would be guesswork; naming the three files planning legitimately produces is
 * not. Anything else inside the task package waits for the plan.
 */
const PLAN_WRITABLE = new Set(["status.txt", "planning.md", "feedback.md"]);

/**
 * Refusals for one tool before the gate steps aside.
 *
 * Two was cheaper to wait out than to satisfy. Measured on the first live run
 * (session t016-live): it refused `web_search` twice, then `web_open` twice,
 * then retired, and the run carried on searching and never claimed the task.
 * Four, each saying something the last did not, costs more than the single
 * write that ends it. It still retires — a gate that can deadlock an
 * unfamiliar project is a gate someone switches off.
 */
/**
 * How many TURNS a rule may refuse before it steps aside — not how many calls.
 *
 * The unit is the whole point. Measured 2026-08-08 on a research run: this
 * model issues five parallel `web_search` calls per turn, so a budget counted
 * in calls was spent inside the first batch, before one refusal had reached the
 * model. The refusal named the next action and nothing read it in time.
 *
 * The ramp exists so a model is not stuck against one wall forever, and being
 * stuck is something that can only happen across turns. 2026-08-06 got the same
 * unit wrong from the other side: the exit was two, claiming cost one write, so
 * absorbing two refusals was cheaper than complying.
 */
const MAX_REFUSAL_TURNS = 4;

export type Phase = "claim" | "plan" | "open";

export interface PhaseBlock {
  block: true;
  reason: string;
}

function read(path: string): string | null {
  try {
    return readFileSync(path, "utf8");
  } catch {
    return null;
  }
}

function leaf(p: string): string {
  return p.replace(/\\/g, "/").split("/").filter(Boolean).pop() ?? "";
}

interface Task {
  name: string;
  dir: string;
  status: string;
}

function tasks(queueDir: string): Task[] {
  let names: string[];
  try {
    names = readdirSync(queueDir);
  } catch {
    return [];
  }
  const out: Task[] = [];
  for (const name of names) {
    if (!/^Task_\d+/.test(name)) continue;
    const dir = join(queueDir, name);
    const status = read(join(dir, "status.txt"));
    if (status === null) continue;
    out.push({ name, dir, status: status.trim() });
  }
  return out;
}

/**
 * The phase a queue is in, or "open" when it cannot tell.
 *
 * More than one open task means the protocol is already being violated in a way
 * another guard reports; this one says nothing rather than guessing which task
 * a call belongs to.
 */
export function phaseOf(queueDir: unknown): Phase {
  if (typeof queueDir !== "string" || !queueDir || !existsSync(queueDir)) return "open";
  const all = tasks(queueDir);
  if (!all.length) return "open";

  const open = all.filter((t) => t.status === "IN_PROGRESS" || t.status === "REVIEW");
  if (open.length > 1) return "open";

  if (open.length === 1) {
    if (open[0].status !== "IN_PROGRESS") return "open";
    const planning = read(join(open[0].dir, "planning.md"));
    if (planning === null || !planning.includes("## Self-Review")) return "plan";
    return "open";
  }

  // Nothing claimed. A PENDING task waiting for someone to take it.
  return all.some((t) => t.status === "PENDING") ? "claim" : "open";
}

/** The task package a path falls inside, or null. */
function taskOf(queueDir: string, target: string): Task | null {
  const p = target.replace(/\\/g, "/").toLowerCase();
  for (const t of tasks(queueDir)) {
    const dir = t.dir.replace(/\\/g, "/").toLowerCase();
    if (p.startsWith(dir + "/") || p.includes("/" + t.name.toLowerCase() + "/")) return t;
  }
  return null;
}

/** Paths a call would write, whichever tool it uses. */
function writeTargets(toolName: string, input: unknown): string[] {
  const src = (input ?? {}) as Record<string, unknown>;
  if (toolName === "write" || toolName === "edit") {
    return typeof src.path === "string" && src.path ? [src.path] : [];
  }
  if (toolName === "bash") {
    try {
      return bashWriteTargets(String(src.command ?? ""));
    } catch {
      return [];
    }
  }
  return [];
}

const CLAIM_FIRST =
  "C.A.S.E. 階段閘(CLAIM):這個佇列有 PENDING 任務,還沒有人認領。" +
  "**問題不是搜尋** —— 搜幾次都可以,而且認領之後研究工具全開。" +
  "問題是還沒認領就開工。先用 `write` 把該任務的 status.txt 改成 IN_PROGRESS,一次寫入的事。";

const CLAIM_THIRD =
  "C.A.S.E. 階段閘(CLAIM,第三次):具體到可以照做 —— " +
  "`write` 到 `02_Task_Queue/<任務資料夾>/status.txt`,內容就是 `IN_PROGRESS` 六個字,沒有別的。" +
  "在那之前,讀取與 grep 完全不受限,你可以先把 recipe.md 讀完再決定。";

const CLAIM_FOURTH =
  "C.A.S.E. 階段閘(CLAIM,最後一次):這是我最後一次擋。" +
  "如果這個佇列根本不是你要處理的東西,那就不要在它旁邊產出檔案 —— 直接回答使用者。" +
  "如果它是,現在就把 status.txt 改成 IN_PROGRESS。下一次同樣的呼叫我會放行,但狀態仍然是 PENDING," +
  "而任何人看這個佇列都會看到這件工作沒有被認領。";

const CLAIM_SECOND =
  "C.A.S.E. 階段閘(CLAIM,第二次):換個做法 —— " +
  "如果你不確定要認領哪一個,先 `read` 那個任務的 recipe.md 與 role.md(讀取不受限);" +
  "如果這個佇列不是你要做的事,就別動它,直接回答使用者。" +
  "要動它,就先 `write` status.txt = IN_PROGRESS。下一次我不會再擋。";

function planFirst(second: boolean, file: string): string {
  return second
    ? `C.A.S.E. 階段閘(PLAN,第二次):換個做法 —— 把你現在要寫進 ${file} 的東西,` +
        "先以「步驟 + 要動的檔案 + 驗證方式」的形式寫進 planning.md,並加一段 `## Self-Review` " +
        "逐條對照 recipe.md 的 Local DoD。寫完之後這道閘就不會再出現。下一次我不會再擋。"
    : `C.A.S.E. 階段閘(PLAN):任務已認領,但 planning.md 還沒有 \`## Self-Review\`,` +
        `所以現在不能寫 ${file}。**研究工具不受限** —— 規劃本來就需要查。` +
        "先寫 planning.md(步驟、要動的檔案、驗證方式 + `## Self-Review`),再產出。";
}

const CLAIM_REASONS = [CLAIM_FIRST, CLAIM_SECOND, CLAIM_THIRD, CLAIM_FOURTH];

export class PhaseGate {
  private refusals = new Map<string, number>();
  /**
   * Rules refused during the current turn, counted once when it ends.
   *
   * Every call in a parallel batch gets the same text on purpose: the model
   * chose all five before reading any of them, so escalating within the batch
   * spends four messages nobody could act on.
   */
  private refusedThisTurn = new Set<string>();

  /**
   * Refuses a call that does not belong to the current phase, or null.
   *
   * Runs after the transition guards on purpose: when both would refuse the
   * same call, theirs is the more specific complaint.
   */
  check(queueDir: unknown, toolName: string, input: unknown): PhaseBlock | null {
    if (typeof queueDir !== "string" || !queueDir) return null;
    let phase: Phase;
    try {
      phase = phaseOf(queueDir);
    } catch {
      return null;
    }
    if (phase === "open") return null;

    // Keyed by PHASE, not by phase-and-tool.
    //
    // It was `${phase}:${toolName}` until 2026-08-08, and the run right after
    // the turn ramp landed showed what that bought: web_search refused through
    // "第三次", then web_open arrived and got "第一次" again, then web_search
    // returned for "最後一次". Rotating tools bought a fresh budget and
    // restarted the escalation, so four research tools meant up to sixteen
    // turns of refusals — which is how the model accumulated enough evidence
    // to conclude the tools were unavailable and stopped searching for the
    // whole run, even after the phase opened.
    //
    // The refusals are about the phase. `web_open` before claiming is the same
    // mistake as `web_search` before claiming, and telling the model "第一次"
    // for the second one misstates how long this has been going on.
    const key = phase;
    const seen = this.refusals.get(key) ?? 0;
    if (seen >= MAX_REFUSAL_TURNS) return null;

    if (phase === "claim") {
      // Read-only until the task is claimed — auto-pi's PLAN shape, applied
      // here. The first live run walked around a research-only rule by writing
      // its 6,358-byte report to `research/…report.md`, outside the queue
      // entirely, where the deliverable rule has no opinion. Reads, greps and
      // status.txt stay open, so the way out is still one write.
      const writes = writeTargets(toolName, input);
      const onlyStatus = writes.length > 0 && writes.every((t) => leaf(t) === "status.txt");
      if (!RESEARCH_TOOLS.has(toolName) && (!writes.length || onlyStatus)) return null;
      this.refusedThisTurn.add(key);
      return { block: true, reason: CLAIM_REASONS[Math.min(seen, CLAIM_REASONS.length - 1)] };
    }

    // PLAN: research is wide open; deliverables wait for the plan.
    const targets = writeTargets(toolName, input);
    if (!targets.length) return null;
    for (const target of targets) {
      const task = taskOf(queueDir, target);
      if (!task) continue;
      const name = leaf(target);
      if (PLAN_WRITABLE.has(name)) continue;
      this.refusedThisTurn.add(key);
      return { block: true, reason: planFirst(seen > 0, name) };
    }
    return null;
  }

  /**
   * Close the turn: each rule that refused at all counts once.
   *
   * Called from the bridge's `turn_end`. Without it the budget never advances
   * and the gate would refuse forever, which is the opposite failure and just
   * as bad — a wall with no door is how a guard gets switched off.
   */
  turnEnded(): void {
    for (const key of this.refusedThisTurn) {
      this.refusals.set(key, (this.refusals.get(key) ?? 0) + 1);
    }
    this.refusedThisTurn.clear();
  }

  /** One session's history. */
  reset(): void {
    this.refusals.clear();
    this.refusedThisTurn.clear();
  }
}
