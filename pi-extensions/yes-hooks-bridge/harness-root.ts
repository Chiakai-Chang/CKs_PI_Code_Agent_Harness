/**
 * The refusal that names the mistake and then supplies the way out.
 *
 * cwd confusion was the largest single failure source measured on 2026-08-06:
 * two of five advancer runs were consumed by it — 11 and 72 refusals, status
 * never leaving PENDING — and a Task_016 run tried to write its report into this
 * repository. Every instance is the same shape: a relative path resolved against
 * the harness install instead of the workspace.
 *
 * It is not mysterious. Pi's system prompt names the harness's absolute path 28
 * times, almost all as `<location>` on skills, and names the cwd once. The
 * belief has a source.
 *
 * The containment guard already refused these and already named the cwd, and the
 * model retried nine times in one run. Today's lesson, measured twice over:
 * refusing removes the wrong path and supplies nothing. So when the target sits
 * inside the harness install while the run is working somewhere else, the same
 * path rewritten into the workspace goes in the refusal, ready to copy.
 *
 * Narrow on purpose. A target elsewhere that has nothing to do with the harness
 * gets the ordinary refusal; inventing a destination would be a guess.
 */

function norm(p: string): string {
  return String(p ?? "").replace(/\\/g, "/").replace(/\/+$/, "");
}

/**
 * A suggested workspace path for a target that landed in the harness install,
 * or null when there is nothing honest to suggest.
 */
export function harnessRootHint(
  target: unknown,
  cwd: unknown,
  harnessRoot: unknown,
): string | null {
  const t = norm(target as string);
  const c = norm(cwd as string);
  const h = norm(harnessRoot as string);
  if (!t || !c || !h) return null;
  // Working inside the harness is not confusion — there is nowhere to redirect.
  if (c.toLowerCase() === h.toLowerCase() || c.toLowerCase().startsWith(h.toLowerCase() + "/")) {
    return null;
  }
  if (!t.toLowerCase().startsWith(h.toLowerCase() + "/")) return null;
  const rest = t.slice(h.length + 1);
  if (!rest) return null;
  return (
    `你要寫的路徑在 **harness 的安裝位置**(${h}),不是你這次的工作目錄(${c})。` +
    `會這樣不奇怪 —— 系統提示裡每個技能的 <location> 都指向那裡,而工作目錄只出現一次。` +
    `但技能住在那裡,工作不放在那裡。` +
    `如果你要的是這次工作目錄裡的同一個位置,路徑是:${c}/${rest}`
  );
}

/**
 * What the workspace actually holds, for a refusal that has said its piece once.
 *
 * Measured across five runs on 2026-08-09/10: four resolved "this project" as
 * the harness install. The redirect hint above fired twice with the corrected
 * absolute path and was ignored both times, and the same refusal repeated
 * verbatim three and two times in one run. A guard repeating itself has taught
 * nothing.
 *
 * The model is not confused; it is reasoning from evidence. Pi's system prompt
 * names the harness root 28 times as skill `<location>` and the cwd once, and on
 * a developer machine that path really does contain a full `02_Task_Queue`. It
 * picked the better-evidenced of two candidate workspaces.
 *
 * So the second refusal stops describing the mistake and shows the other half of
 * the evidence: what is in the working directory, by name. This is the fix that
 * worked for the CLAIM gate's third rung — the run after it landed was the first
 * to return to its own cwd unaided.
 *
 * Falsifiable prediction, written before the runs that test it: across three
 * runs of the same scenario, claims inside the harness queue should fall and
 * claims inside the workspace queue should rise. If all three are unchanged,
 * this is the fourth failed attempt to fix behaviour by adding words, and the
 * next move is structural rather than textual.
 */
export function workspaceListing(
  cwd: unknown,
  entries: (dir: string) => string[],
  isDir: (p: string) => boolean,
): string | null {
  const c = norm(cwd as string);
  if (!c) return null;
  let top: string[];
  try {
    top = entries(c).filter((n) => !n.startsWith(".")).slice(0, 12);
  } catch {
    return null;
  }
  if (!top.length) return null;
  const lines: string[] = [`你這次的工作目錄是 ${c},裡面有:`];
  for (const name of top) {
    let tasks: string[] = [];
    if (name === "02_Task_Queue") {
      try {
        tasks = entries(`${c}/${name}`).filter((n) => /^Task_\d+/.test(n)).slice(0, 6);
      } catch {
        tasks = [];
      }
    }
    let suffix = "";
    try {
      suffix = isDir(`${c}/${name}`) ? "/" : "";
    } catch {
      suffix = "";
    }
    lines.push(tasks.length
      ? `  - ${name}${suffix}  ← 這裡面有:${tasks.join("、")}`
      : `  - ${name}${suffix}`);
  }
  lines.push("**你要處理的東西在上面這份清單裡,不在 harness 的安裝目錄。**");
  return lines.join("\n");
}

/**
 * The whole refusal for a write that landed outside the project root.
 *
 * This lives here rather than being formatted inline in `index.ts` because of
 * how Task_003's second surviving break got away: the test read `index.ts` and
 * looked for `harnessRootHint(...)` near `reason:`, and replacing the call with
 * `null` left it green — the identifier appeared twice in that expression and
 * the assertion was textual. Tightening the regex would not have fixed it.
 * `index.ts` needs Pi's runtime, so nothing in it is driven by a behavioural
 * test, and a string assertion is the only kind available there.
 *
 * A pure function is testable, and it is inside the mutation sweep. This is the
 * pure-logic/runtime split the repo already uses for `phase-gate.ts`, taken
 * from auto-pi's `workflow-gate-logic.ts`.
 */
export function containmentRefusal(
  toolName: unknown,
  target: unknown,
  cwd: unknown,
  harnessRoot: unknown,
  /** How many times this guard has already refused this session. */
  seen = 0,
  /** Directory listing, injected so this stays a pure, testable function. */
  listing?: () => string | null,
): string {
  const base =
    `Directory containment: ${String(toolName)} target "${String(target)}" is ` +
    `outside the project root (${String(cwd)}). Write inside the project you ` +
    `were launched in. If you truly need to touch another directory, ask the user.`;
  const hint = harnessRootHint(target, cwd, harnessRoot);
  const parts = [base];
  if (hint) parts.push(hint);
  // From the second refusal on, stop restating the mistake and show what the
  // workspace holds. The first refusal has already said everything description
  // can say, and it was measured being ignored twice with the corrected path in
  // hand — while the same text repeated three times in one run. See
  // workspaceListing for the evidence and the falsifiable prediction.
  if (seen >= 1 && listing) {
    let shown: string | null = null;
    try {
      shown = listing();
    } catch {
      shown = null;
    }
    if (shown) {
      parts.push(
        `同樣的理由已經擋你第 ${seen + 1} 次了,所以這次不重複講,直接給你看:\n${shown}`);
    }
  }
  return parts.join("\n\n");
}
