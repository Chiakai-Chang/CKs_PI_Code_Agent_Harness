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
import { join } from "node:path";

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
    text: clip([header, ...parts, footer].join("\n\n"), MAX_TASK_CONTEXT_CHARS),
    sources,
  };
}
