import { ENVELOPE_TAIL_BYTES } from "./constants.ts";
import type { JobRecord } from "./jobs.ts";

/** Keep the end of the output — the failure is almost always at the tail.
 *
 *  Counts UTF-8 bytes, as the name and ENVELOPE_TAIL_BYTES both claim. Slicing
 *  by JS string length instead meant a 4 KiB budget injected about 12 KiB of
 *  CJK output, and could cut a character in half. After taking the last `max`
 *  bytes the start is advanced past any continuation byte (`10xxxxxx`) so the
 *  result always begins on a character boundary — which also keeps astral
 *  characters like emoji intact, since UTF-8 encodes a whole code point. */
export function tailBytes(s: string, max: number): string {
  const buf = Buffer.from(s, "utf8");
  if (buf.length <= max) return s;
  let start = buf.length - max;
  while (start < buf.length && (buf[start] & 0xc0) === 0x80) start++;
  return buf.subarray(start).toString("utf8");
}

export function buildEnvelope(jobs: JobRecord[], tails: Map<string, string>): string {
  const lines: string[] = [
    "[async-exec] Background work finished. Continue from where you stopped;" +
      " if nothing is outstanding, say so and stop rather than inventing work.",
  ];
  for (const j of jobs) {
    const secs = j.endedAt === null ? 0 : (j.endedAt - j.startedAt) / 1000;
    lines.push(
      `[bg] job ${j.id} · "${j.label}" · ${j.state} · exit=${j.exitCode ?? "n/a"} · ${secs.toFixed(1)}s`,
    );
    lines.push(`     full output: ${j.outPath}`);
    const tail = tails.get(j.id);
    if (tail) {
      lines.push(`     tail:\n${tailBytes(tail, ENVELOPE_TAIL_BYTES)}`);
    }
  }
  return lines.join("\n");
}
