import { ENVELOPE_TAIL_BYTES } from "./constants.ts";
import type { JobRecord } from "./jobs.ts";

/** Keep the end of the output — the failure is almost always at the tail. */
export function tailBytes(s: string, max: number): string {
  if (s.length <= max) return s;
  return s.slice(s.length - max);
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
