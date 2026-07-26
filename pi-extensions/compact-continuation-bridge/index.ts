/**
 * Compact Continuation Bridge
 *
 * Pi's own compact() unconditionally aborts the current agent operation first,
 * and for "manual" or "threshold" compaction reasons, `willRetry` is always
 * false — the engine's comment: "Threshold: Context over threshold, compact,
 * NO auto-retry (user continues manually)". Only "overflow" (context blew past
 * the hard limit) auto-retries the aborted turn on its own.
 *
 * That means every /compact, every threshold-triggered auto-compaction, and
 * every extension-triggered ctx.compact() (e.g. stealth-web-bridge's proactive
 * guard) leaves Pi sitting idle afterward, even mid-task — the user has to type
 * something to get the agent moving again. This bridge closes that gap: after
 * any compaction that Pi itself won't auto-retry, it queues a continuation
 * follow-up so the agent picks back up on its own.
 *
 * Compaction hook choice: session_compact is used (not session_before_compact)
 * because mutation before compaction is ineffective — Pi's compaction may
 * discard pre-compact prompt changes. The continuation message uses a verbatim-
 * preservation block header so lossy compaction keeps the critical signals.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

/**
 * Compaction survival kit: the verbatim-preservation header tells Pi's lossy
 * compaction to keep the content below — the goal, verify command, and
 * evidence are the bytes most worth keeping across a compaction boundary.
 * Inspired by pi-until-done's compaction-context.ts pattern.
 *
 * The generic continuation body is intentionally brief; planning-with-files
 * bridge already injects plan context (task_plan.md + recent progress) via
 * before_agent_start, so the agent retains task awareness on the resumed turn.
 */
const CONTINUE_MESSAGE =
  "[compact-continuation · compaction context — preserve everything below verbatim]" +
  "\n壓縮（compact）已完成。若你原本正在進行某項尚未完成的工作，請直接接續完成，不需要重新詢問或等待進一步指示。" +
  "實測紀律：任何完成聲明必須有實際命令輸出作為證據，不接受編譯成功、自行添加的測試通過或「看起來對了」作為完成證明。" +
  "若當下沒有未完成的工作，請直接說明目前狀態並停止，不要編造新的任務。";

export default function (pi: ExtensionAPI) {
  pi.on("session_compact", async (event, ctx) => {
    // willRetry is true only for overflow recovery — Pi's own engine already
    // retries the aborted turn itself in that case. Sending our own
    // continuation on top would double up (two turns racing/queued).
    if (event.willRetry) return;

    ctx.ui?.notify?.(
      `[compact-continuation] Compaction (${event.reason}) complete — queuing a continuation follow-up.`,
      "info",
    );

    pi.sendMessage(
      {
        customType: "compact-continuation",
        content: CONTINUE_MESSAGE,
        display: true,
      },
      { deliverAs: "followUp", triggerTurn: true },
    );
  });
}
