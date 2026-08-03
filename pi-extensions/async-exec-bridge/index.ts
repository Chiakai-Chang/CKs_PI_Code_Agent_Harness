/**
 * Async Exec Bridge
 *
 * Dispatches long-running work without blocking the agent, and wakes the agent
 * when that work finishes. Compaction continuation is already handled by
 * compact-continuation-bridge; this covers long programs and subagents.
 *
 * Verified platform facts this depends on:
 *   - an extension's event loop survives an idle agent, and detached
 *     setTimeout fires on time;
 *   - pi.sendMessage(msg, { triggerTurn: true, deliverAs: "followUp" }) wakes
 *     an idle agent.
 * See docs/retro/2026-08-03-absence-is-not-impossibility.md
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  void pi;
}
