/**
 * Plan detection and command recognition for ecc-hooks-bridge.
 *
 * The bridge used to answer "is there a plan?" with a single
 * `existsSync(join(process.cwd(), "task_plan.md"))`, while
 * planning-with-files-bridge answered the same question with `resolvePlanDir()`
 * — which also honours `.planning/.active_plan` and `.planning/<id>/task_plan.md`.
 * A plan kept anywhere but the repo root was therefore invisible here, and every
 * commit drew a nag for a plan that existed.
 *
 * `resolvePlanDir` below is deliberately the same algorithm as the one in
 * planning-with-files-bridge. Duplicated logic that nobody compares is exactly
 * how uninstall.py came to manage 5 bridges against restore.py's 11, so
 * tests/test_plan_detection_parity.py runs both implementations over the same
 * layouts and fails when they stop agreeing.
 */

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

function fileExists(dir: string, name: string): boolean {
  return existsSync(join(dir, name));
}

/** Directory holding the active plan, or `cwd` when there is none. */
export function resolvePlanDir(cwd: string): string {
  if (fileExists(cwd, "task_plan.md")) return cwd;

  const planningDir = join(cwd, ".planning");
  if (!fileExists(cwd, ".planning")) return cwd;

  if (fileExists(planningDir, ".active_plan")) {
    try {
      const activeId = readFileSync(join(planningDir, ".active_plan"), "utf8").trim();
      const candidate = join(planningDir, activeId);
      if (existsSync(candidate) && fileExists(candidate, "task_plan.md")) return candidate;
    } catch {}
  }

  if (existsSync(planningDir)) {
    try {
      const dirs = readdirSync(planningDir, { withFileTypes: true })
        .filter(d => d.isDirectory())
        .map(d => join(planningDir, d.name))
        .filter(d => fileExists(d, "task_plan.md"));
      if (dirs.length > 0) return dirs[dirs.length - 1];
    } catch {}
  }

  return cwd;
}

/** Whether a plan exists anywhere this project keeps one. */
export function hasAnyPlan(cwd: string): boolean {
  return fileExists(resolvePlanDir(cwd), "task_plan.md");
}

/**
 * Whether this project runs the C.A.S.E. protocol, in which case the routine
 * this bridge hands out is the wrong advice.
 *
 * The routine says "load planning-with-files and write task_plan.md". A C.A.S.E.
 * project plans inside the task package — `planning.md` with a `## Self-Review`,
 * which its own phase gate refuses deliverables without. Two planning systems
 * that cannot see each other was measured on 2026-08-10: `hasAnyPlan` looks for
 * `task_plan.md` and finds none in a queue project, so the routine fires and
 * points at an artifact nothing there will ever read; conversely one stray
 * `task_plan.md` at a project root suppresses the routine for every task in the
 * queue.
 *
 * So this bridge stands down and the task-local constitution carries the task's
 * own planning and methodology instead — the same shape as the phase gate
 * yielding to directory containment: whoever has the more specific complaint
 * speaks, and only one of them can.
 *
 * The two-file test is duplicated from `case-bridge/index.ts` rather than
 * imported: bridges install as sibling directories with no dependency between
 * them, and reaching across would break this one whenever the other is
 * uninstalled. It is a filesystem predicate, not logic — the classifier itself
 * is NOT duplicated, which is the mistake this repo already made once.
 */
export function isCaseProject(cwd: string): boolean {
  return fileExists(cwd, "CASE.md") || fileExists(cwd, "00_Constitution");
}

/** Command separators that start a fresh command word. */
const SEGMENT_SPLIT = /(?:&&|\|\||[;|\n])/;

/**
 * Whether a bash command actually commits.
 *
 * The old test was `command.includes("git commit")`, which fired on `echo "git
 * commit"`, on grepping the docs for the phrase, and on writing a file that
 * merely contained it. Quoted text is stripped before matching for that reason,
 * and `commit-graph` is not `commit`.
 */
export function isGitCommit(command: string): boolean {
  if (!command) return false;

  const unquoted = command.replace(/"[^"]*"/g, " ").replace(/'[^']*'/g, " ");

  return unquoted.split(SEGMENT_SPLIT).some(segment => {
    const s = segment.trim();
    // `-C <dir>` and `-c <key=value>` put their value in the next word, so the
    // subcommand is two tokens further along than a plain flag leaves it.
    if (!/^git\s+(?:-[Cc]\s+\S+\s+|-\S+\s+)*commit(?:\s|$)/.test(s)) return false;
    // `git commit --help` opens the manual; it does not create a commit.
    if (/(?:^|\s)(?:--help|-h)(?:\s|$)/.test(s)) return false;
    return true;
  });
}
