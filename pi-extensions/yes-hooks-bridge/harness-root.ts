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
