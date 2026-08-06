/**
 * A reply that came back as a compaction summary instead of the answer.
 *
 * Session 019fd702, 2026-08-06, real use. The turn did the work — 15 searches,
 * 10 pages opened, 14 writes, and a 9,092-char `ach-analysis-report.md` with
 * five competing hypotheses and thirteen pieces of evidence carrying URLs. The
 * reply the user then read, 6,466 chars, opened with:
 *
 *     <analysis>
 *     Let me chronologically analyze the conversation:
 *
 *     1. **First User Message (Message 1)**: User provided a massive block of ...
 *
 * That is Pi's own compaction output shape — `dist/core/messages.js` wraps a
 * compacted history in `<summary>` behind the prefix "The conversation history
 * before this point was compacted into the following summary:". The session
 * record has zero compaction events. The model produced the artifact
 * spontaneously and it stood in place of the deliverable.
 *
 * The cost was two wrong diagnoses. Reading that reply, the owner concluded
 * planning-with-files had stopped being used and that the run was emitting tags
 * matching no tool. Neither was true: task_plan.md, findings.md and progress.md
 * were written and edited throughout and the session's last two actions were
 * writes. One substituted reply misrepresented a session that had gone well.
 *
 * Related to the guard for compaction's own `<read-files>` tags being echoed as
 * fake tool calls — same family, different artifact. That one watches for
 * tool-shaped markup; this one watches for the envelope around a summary.
 *
 * Deliberately narrow. `<summary>` is ordinary HTML inside `<details>` and this
 * repo's own documents use it, so only a reply that OPENS with the envelope
 * counts, and a genuine compaction is exempt because it carries Pi's prefix.
 */

/**
 * The envelope, at the very start of the reply.
 *
 * "At the very start" is doing two jobs. It excludes a `<details>` disclosure
 * block, which legitimately carries a `<summary>` immediately after its opening
 * tag — this repo's own documents are full of them. And it excludes a genuine
 * compaction, because Pi always writes its prefix first: "The conversation
 * history before this point was compacted into the following summary:". A real
 * summary therefore never opens with the bare tag.
 *
 * The first draft also carried an explicit exemption matching that prefix.
 * Breaking it changed nothing — the envelope check had already returned by
 * then, so the exemption could not run. A check that cannot fire is worse than
 * no check, because it reads as a safety net.
 */
const OPENS_WITH_ENVELOPE = /^\s*<(analysis|summary)>/i;

export interface EchoCorrection {
  message: string;
}

/**
 * Returns a correction when a reply is a compaction summary that nobody asked
 * for, or null.
 *
 * `written` is whatever the turn wrote, used to point at the deliverable that
 * exists — the answer is usually already on disk, which is what makes this
 * worth correcting rather than re-running.
 */
export function compactionEcho(finalText: string, written?: readonly string[]): EchoCorrection | null {
  const text = String(finalText || "");
  if (!text.trim()) return null;
  if (!OPENS_WITH_ENVELOPE.test(text)) return null;

  const files = (written ?? []).filter((f) => typeof f === "string" && f);
  const pointer = files.length
    ? `這一輪實際寫出的檔案是:${files.join("、")}。請直接把其中的結論講給使用者聽。`
    : `如果成果已經寫進檔案,請直接把結論講出來;如果還沒,請先做完再回覆。`;

  return {
    message:
      `[SYSTEM] 你這一輪的回覆以 \`<analysis>\` / \`<summary>\` 開頭,那是 Pi **壓縮對話歷史**` +
      `時使用的格式 —— 而這一輪沒有發生壓縮,使用者要的也不是對話流水帳。\n\n` +
      `實測過一次同樣的狀況:工作全部做完了(15 次搜尋、10 次開頁、9,092 字元的報告),` +
      `使用者看到的卻是對話回顧,於是誤以為整套流程沒有運作。\n\n${pointer}`,
  };
}
