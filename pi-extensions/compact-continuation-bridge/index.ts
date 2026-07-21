/**
 * Compact Continuation Bridge
 *
 * Pi's own compact() (dist/core/agent-session.js) unconditionally aborts the
 * current agent operation first, and for "manual" or "threshold" compaction
 * reasons, `willRetry` is always false — the engine's own comment says it
 * outright: "Threshold: Context over threshold, compact, NO auto-retry (user
 * continues manually)". Only "overflow" (context genuinely blew past the
 * hard limit) auto-retries the aborted turn on its own.
 *
 * That means every /compact, every threshold-triggered auto-compaction, and
 * every extension-triggered ctx.compact() (e.g. stealth-web-bridge's
 * proactive guard) leaves Pi sitting idle afterward, even mid-task — the
 * user has to type something to get the agent moving again. This bridge
 * closes that gap: after any compaction that Pi itself won't auto-retry, it
 * queues a generic "continue what you were doing" follow-up so the agent
 * picks back up on its own.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const CONTINUE_MESSAGE =
  "壓縮（compact）已完成。若你原本正在進行某項尚未完成的工作，請直接接續完成，不需要重新詢問或等待進一步指示。" +
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
