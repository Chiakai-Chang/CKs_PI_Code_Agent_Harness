/**
 * The task's own constitution, put in front of the model when it claims the task.
 *
 * Every C.A.S.E. task package ships a `role.md` — "You are a Principal Security
 * Architect..." — and a `recipe.md` carrying an Objective and a Local Definition
 * of Done. The owner's mental model was that these act like a local AGENTS.md:
 * claim a task, and its own rules come with it.
 *
 * They never did. Searching this repo for `role.md` finds exactly two hits and
 * neither loads it: a line in `phase-gate.ts` SUGGESTING the model go read it,
 * and a table in a docs page. A week of measurement here says the same thing
 * every time — a suggestion is skipped, an injection and a refusal are not.
 *
 * And the file could not simply be re-read later, because moving to the next task
 * does not start a new prompt cycle. The advancer continues with
 * `sendMessage({ customType }, { deliverAs: "followUp", triggerTurn: true })`,
 * and session 019fcf32 shows that custom message sitting between two assistant
 * turns with no user message between. `before_agent_start` fires "after user
 * submits prompt"; no user message, no re-injection. Every task in a queue run
 * shares one prompt cycle, and the Constitution, the Roadmap and the task's own
 * role are all stated once, at the very beginning, for all of them.
 *
 * So this rides the claim itself — the moment `status.txt` becomes IN_PROGRESS,
 * on a tool result, which is one of the two channels measured to reach the model
 * in this harness.
 *
 * Why this shape beats the step counter in `task-shape-bridge/goal-restate.ts`:
 * that one fires at the 12th tool result, a number that had to be calibrated
 * against a distribution, and proving it works needs a control arm that drifts —
 * three attempts failed to build one. This fires at a semantic boundary that
 * needs no calibration, and the question "did it arrive" is answerable from one
 * session log. Alignment afterwards is not a metric anyone has to invent either:
 * the protocol already wrote it down as that task's Local DoD.
 */

import { existsSync, readFileSync } from "node:fs";
import { basename, join } from "node:path";

/**
 * Total budget for the injected block.
 *
 * It rides a tool result the model is already reading, and this harness has
 * measured what happens when an injection competes with the thing it is attached
 * to. `caseBridgeMaxChars` is 600 for the Constitution; a task's own rules are
 * more specific and more actionable than the global ones, so they get more —
 * but not so much that the tool's own output disappears underneath them.
 */
export const MAX_TASK_CONTEXT_CHARS = 1200;

/** Per-section caps, so one long file cannot crowd out the others. */
const MAX_ROLE_CHARS = 500;
const MAX_SECTION_CHARS = 600;

/**
 * A named section of a markdown file, heading excluded.
 *
 * Matches `## Objective`, `## Local Definition of Done (DoD)`, `## 目標` —
 * the heading text only has to START with the name, because the protocol's own
 * templates append parentheticals and translations to their headings.
 */
export function section(markdown: unknown, name: string): string {
  const text = typeof markdown === "string" ? markdown : "";
  if (!text || !name) return "";
  const lines = text.split(/\r?\n/);
  const want = name.toLowerCase();
  let depth = 0;
  const out: string[] = [];
  for (const line of lines) {
    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      const level = heading[1].length;
      const title = heading[2].trim().toLowerCase();
      if (depth === 0) {
        if (title.startsWith(want)) depth = level;
        continue;
      }
      // A heading at the same level or higher ends the section; a deeper one is
      // part of it. Ending on ANY heading was the first version, and it truncated
      // a Local DoD that had a `### Evidence` sub-heading in the middle.
      if (level <= depth) break;
    }
    if (depth > 0) out.push(line);
  }
  return out.join("\n").trim();
}

function clip(text: string, max: number): string {
  const t = text.trim();
  if (t.length <= max) return t;
  return t.slice(0, max) + " …(截斷)";
}

function readIfPresent(dir: string, name: string): string {
  const p = join(dir, name);
  try {
    return existsSync(p) ? readFileSync(p, "utf8") : "";
  } catch {
    return "";
  }
}

export interface TaskConstitution {
  /** The block to inject. */
  text: string;
  /** Which files actually contributed — for the notify line and for tests. */
  sources: string[];
}

/**
 * The task's local constitution, or null when the package carries none.
 *
 * Returns null rather than an empty block when there is nothing to say. An
 * injected header with nothing under it teaches the model that this channel
 * carries noise, and the next real one gets skimmed.
 */
export function localConstitution(taskDir: unknown): TaskConstitution | null {
  const dir = String(taskDir ?? "");
  if (!dir) return null;

  const role = clip(readIfPresent(dir, "role.md")
    .replace(/^#\s+.*$/m, "").trim(), MAX_ROLE_CHARS);
  const recipe = readIfPresent(dir, "recipe.md");
  // Both spellings: the vendored templates use English headings, and a project
  // written in Chinese uses 目標 / 驗收. Checking one and shipping was how the
  // skill catalogue ended up unreadable to half the projects that had one.
  const objective = clip(section(recipe, "objective") || section(recipe, "目標"),
                         MAX_SECTION_CHARS);
  const dod = clip(section(recipe, "local definition of done")
                   || section(recipe, "definition of done")
                   || section(recipe, "local dod")
                   || section(recipe, "驗收"), MAX_SECTION_CHARS);

  const parts: string[] = [];
  const sources: string[] = [];
  if (role) {
    parts.push(`**你在這個任務裡的角色**\n${role}`);
    sources.push("role.md");
  }
  if (objective) {
    parts.push(`**這個任務的目標**\n${objective}`);
    if (!sources.includes("recipe.md")) sources.push("recipe.md");
  }
  if (dod) {
    parts.push(`**這個任務的驗收標準(Local DoD)**\n${dod}`);
    if (!sources.includes("recipe.md")) sources.push("recipe.md");
  }
  if (!parts.length) return null;

  const header =
    "[C.A.S.E.] 任務專屬憲法(不是指令輸出) —— " +
    "以下規則只適用於你剛認領的這個任務,優先於一般性的做法:";
  const footer =
    "完成前請逐條對照上面的 Local DoD,並附上實際跑過的指令與輸出;" +
    "驗不了的部分要明講,不要用「應該可以」帶過。";

  return {
    text: clip([header, ...parts, methodology(objective), footer].join("\n\n"),
               MAX_TASK_CONTEXT_CHARS),
    sources,
  };
}

/** Extensions a Local DoD names when it means "produce this file". */
const ARTIFACT = /\b([A-Za-z0-9_.-]+\.(?:md|txt|json|jsonl|csv|ya?ml))\b/g;

/**
 * Files the Local DoD asks for that do not exist yet.
 *
 * The gap this closes, measured 2026-08-10 in session 019febe9. Every guard did
 * its job and the composition still let a task reach REVIEW with nothing in it:
 *
 *     write output.md            -> refused (phase gate: not claimed yet)
 *     status.txt = DONE          -> refused (transition: PENDING>DONE skips)
 *     status.txt = IN_PROGRESS   -> allowed
 *     status.txt = DONE          -> refused (transition: IN_PROGRESS>DONE skips)
 *     status.txt = REVIEW        -> allowed
 *
 * Final state REVIEW, with no output.md and no planning.md. The run had actually
 * written the report — the refused call carried a complete retries table — and
 * after claiming it never wrote it again. It tried twice to jump to DONE, was
 * refused both times, and took the legal road instead. A threshold defines the
 * shape of the evasion, and the legal road asked for no artifacts at all.
 *
 * REVIEW is the state that summons a human under Path A, so this is the
 * difference between asking someone to accept work and asking them to accept an
 * empty folder.
 *
 * Deliberately narrow. Only names with a document extension count — a DoD line
 * saying "run the tests" asks for no file and must not be turned into one — and
 * a name that exists anywhere in the workspace passes, because a DoD may cite an
 * input it did not create. Fails open on a missing or unparsable recipe: a task
 * package that never said what it owes cannot be held to it.
 */
export function missingDodArtifacts(
  taskDir: unknown,
  cwd: unknown,
  exists: (p: string) => boolean,
): string[] {
  const dir = String(taskDir ?? "");
  if (!dir) return [];
  const dod = section(readIfPresent(dir, "recipe.md"), "local definition of done")
    || section(readIfPresent(dir, "recipe.md"), "definition of done")
    || section(readIfPresent(dir, "recipe.md"), "驗收");
  // No early return for an empty DoD: `"".matchAll` yields nothing and the
  // function returns [] two lines later. The mutation sweep survived deleting
  // the guard, which is what unreachable means.
  const wanted = new Set<string>();
  for (const m of dod.matchAll(ARTIFACT)) wanted.add(m[1]);
  // status.txt is the thing being written right now, and recipe/role are inputs.
  for (const own of ["status.txt", "recipe.md", "role.md"]) wanted.delete(own);
  const roots = [dir, String(cwd ?? "")].filter(Boolean);
  return [...wanted].filter(
    (name) => !roots.some((r) => exists(join(r, name))));
}

/**
 * Signals that pick which methodology to name. NOT a request classifier.
 *
 * `task-shape-bridge/shape.ts` classifies request shape and is deliberately not
 * reused here: bridges install as sibling directories with no dependency
 * between them, and this repo has already paid for duplicating that classifier
 * once. These are a handful of literal words matched against one task's
 * Objective, used only to decide which of three skill names to put first. When
 * none match, the planning line still goes out — that is the part the phase gate
 * enforces, and it is never conditional.
 */
const DEBUG_WORDS = /(?:除錯|偵錯|修[復正]|bug|失敗|錯誤|debug|fix|broken|regression)/i;
const RESEARCH_WORDS = /(?:研究|調查|盤點|比較|評估|審視|survey|research|compare|evaluate|audit)/i;
const BUILD_WORDS = /(?:實作|開發|新增|建立|implement|build|add|create|refactor)/i;

/**
 * The methodology line for this task.
 *
 * The gap this closes, found 2026-08-10: the harness routes methodology from the
 * USER's message, at `before_agent_start`, once per prompt. A queue run's user
 * message is "繼續"; the multi-step work is described in the task's recipe.md,
 * which nothing read. So Global had planning and methodology routing while a
 * claimed task had only a template — the phase gate says "write planning.md with
 * steps, files and a verification method", which is a FORM, not a METHOD.
 *
 * Kept to two sentences. It rides a tool result alongside the role and the DoD,
 * and a paragraph of process advice there competes with the task itself.
 */
export function methodology(objective: string): string {
  const text = String(objective ?? "");
  const skills: string[] = [];
  if (DEBUG_WORDS.test(text)) skills.push("`systematic-debugging`");
  if (RESEARCH_WORDS.test(text)) skills.push("`brainstorming`(先把要查什麼問清楚)");
  if (BUILD_WORDS.test(text)) skills.push("`test-driven-development`");
  const named = skills.length
    ? `這個任務的形狀適合先載入 ${skills.join(" 或 ")};`
    : "動手前先想清楚用什麼方法(除錯用 `systematic-debugging`," +
      "新做的東西先 `brainstorming`,實作用 `test-driven-development`);";
  return (
    "**做法**\n" + named +
    "**方法先於動手,不要跳過**。" +
    "然後把步驟、要動的檔案、驗證方式寫進這個任務資料夾的 `planning.md`," +
    "並加一節 `## Self-Review` 逐條對照上面的 Local DoD —— " +
    "**在那之前階段閘不會讓你寫交付物**。" +
    "計畫寫在任務包裡,不是 `task_plan.md`。"
  );
}

/** How much of the goal rides along mid-run. It shares a tool result. */
const MAX_RESTATE_CHARS = 400;

/**
 * The goal to put back in front of the model, taken from the TASK.
 *
 * T-A3. `task-shape-bridge/goal-restate.ts` restates the user's own request,
 * which is the right source outside a C.A.S.E. project and the wrong one inside
 * it: measured 2026-08-11, the real prompt for a queue run is 「請處理
 * 02_Task_Queue 裡待辦的任務」, which names no goal at all. It also classifies
 * as single-step, so that mechanism has never armed in any C.A.S.E. run — the
 * injection tables for runs 4 through 7 show only the constitution and the
 * phase notice.
 *
 * The Local DoD is preferred over the Objective because it is the thing the
 * work is checked against, and because the run that motivated all of this
 * reached REVIEW having done one item of eleven.
 */
export function taskGoal(taskDir: unknown): string | null {
  const dir = String(taskDir ?? "");
  if (!dir) return null;
  const recipe = readIfPresent(dir, "recipe.md");
  const dod = section(recipe, "local definition of done")
    || section(recipe, "definition of done")
    || section(recipe, "local dod")
    || section(recipe, "驗收");
  const goal = dod || section(recipe, "objective") || section(recipe, "目標");
  const text = clip(goal.replace(/\s*\n\s*/g, "\n").trim(), MAX_RESTATE_CHARS);
  return text || null;
}

/**
 * Mid-run restatement for a C.A.S.E. task.
 *
 * `before_agent_start` fires once per USER MESSAGE, and moving to the next task
 * uses a custom message, so everything stated at the start of a run is as many
 * turns behind as the run is long. Session 019fe60f: one user message, sixteen
 * assistant turns.
 *
 * Counts RESULTS, not calls, and says so in the text — turns emit tool calls in
 * batches, and an extension's counter reaching 12 while the model has issued 14
 * is a number the model can see is wrong.
 *
 * Errors do not count. A refused call is not progress, and counting it would
 * interrupt the run least able to use a reminder as anything but noise.
 */
export class TaskGoalRestate {
  private goal: string | null = null;
  private task = "";
  private acts = 0;
  private sent = 0;
  private readonly threshold: number;
  private readonly max: number;

  constructor(threshold: number, max: number) {
    this.threshold = threshold;
    this.max = max;
  }

  /**
   * Arm on the task that was just claimed. A new task is a new goal.
   *
   * The SAME task re-arms nothing. `claimedTaskDir` reports every successful
   * write that leaves status.txt reading IN_PROGRESS, not only the transition,
   * so a model that writes its claim twice would reset the counter and push the
   * reminder further away each time — the reminder would be quietest in exactly
   * the run that repeats itself.
   */
  claimed(taskDir: unknown): void {
    const name = basename(String(taskDir ?? ""));
    if (name && name === this.task) return;
    this.goal = taskGoal(taskDir);
    this.task = name;
    this.acts = 0;
    this.sent = 0;
  }

  afterToolResult(isError: unknown): string | null {
    if (!this.goal) return null;
    if (isError === true) return null;
    this.acts++;
    if (this.acts < this.threshold) return null;
    if (this.sent >= this.max) return null;
    this.sent++;
    const at = this.acts;
    this.acts = 0;
    return `[C.A.S.E.] 目標重述(不是指令輸出) —— 距離認領 ${this.task} 已經過 ` +
      `${at} 個工具結果。這個任務的驗收標準是:\n${this.goal}\n` +
      `對照一下:哪幾條已經有證據,哪幾條還沒有。`;
  }

  /** A new session is a new run. */
  reset(): void {
    this.goal = null;
    this.task = "";
    this.acts = 0;
    this.sent = 0;
  }
}
