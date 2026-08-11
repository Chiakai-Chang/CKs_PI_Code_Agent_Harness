/**
 * What the model is told about MECE-Autopilot, and where to run it.
 *
 * Split out of `index.ts` so it can be driven by a test: that file opens with
 * `require.resolve`, which exists only under Pi's shim, so anything left inside
 * it is covered by nothing.
 *
 * The line that matters is the last one, and it exists because of run 10
 * (2026-08-12). The bridge already injected the orchestrator's ABSOLUTE path,
 * and the model still ran:
 *
 *     cd "<harness repo>" && node "external/mece-autopilot/scripts/…" --init "…"
 *
 * from a session whose workspace was somewhere else entirely, creating `wiki/`
 * and `skills/` inside the harness. The orchestrator writes its state relative
 * to wherever it runs, and the old text finished by telling the model to look
 * for `wiki/.mece_state.json` — a relative path, with nothing saying which
 * directory it should be relative to. An instruction that does not name the
 * working directory leaves the model to pick one, and it picked the directory
 * the script lives in.
 *
 * Containment now refuses that crossing (`bash-containment.ts::relocatedWrite`),
 * but a refusal is the second line. The first is not pulling the model there.
 */
export function buildNotice(orchestratorScript: string): string[] {
  return [
    `[MECE-Autopilot] MECE-Autopilot reasoning engine is available in this harness.`,
    `- To initialize a new MECE roundtable discussion for a decision: node "${orchestratorScript}" --init "<problem_description>"`,
    `- To verify current step and progress to next expert/round: node "${orchestratorScript}" --step`,
    `- To view current discussion status: node "${orchestratorScript}" --status`,
    `- To reset state: node "${orchestratorScript}" --reset`,
    `**Run it from YOUR workspace, never from the harness.** The script writes ` +
    `wiki/ and its state beside whatever directory it runs in, so \`cd\` into ` +
    `the harness would leave a discussion inside someone else's project — a ` +
    `live run did exactly that. The path above is absolute on purpose: call it ` +
    `where you are.`,
    `If MECE-Autopilot is active (check whether wiki/.mece_state.json exists ` +
    `IN YOUR WORKSPACE), follow the active instructions in wiki/next_task.md there.`,
  ];
}
