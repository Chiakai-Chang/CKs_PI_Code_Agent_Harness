/**
 * Tool-output truncation for the stealth web tools.
 *
 * Pi truncates its OWN read tool at 2000 lines / 50KB (engine:
 * dist/core/tools/truncate.d.ts). These web tools were returning up to 80,000
 * chars. Measured across this machine's session history: web_open results ran
 * to a median of 9,319 chars, p90 36,593, max 80,029 — roughly 20K tokens in a
 * single tool result. That size is not hypothetical harm: a 42,999-char result
 * from an unrelated tool was observed derailing this exact local model
 * mid-task, and the bridge's previous mitigation was to compact the entire
 * context afterwards, which treats the overflow instead of the cause.
 *
 * Approach borrowed from pi-browser-harness (research/pi-browser-harness,
 * src/util/truncate.ts): cut to the standard budget and spill the remainder to
 * a file, naming the path in the result, so the model keeps a usable excerpt
 * and can still reach the rest deliberately.
 *
 * This file deliberately imports nothing but node builtins. index.ts pulls in
 * `typebox`, which bare `node` cannot resolve, so anything living there cannot
 * be executed by a test — and an untested size guard is exactly the kind of
 * thing that silently stops working.
 */
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

export const MAX_TOOL_LINES = 2000;
export const MAX_TOOL_BYTES = 50_000;

export function humanSize(bytes: number): string {
  return bytes < 1024
    ? `${bytes}B`
    : bytes < 1024 * 1024
      ? `${(bytes / 1024).toFixed(1)}KB`
      : `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

export function truncateForTool(output: string, prefix: string): string {
  const totalBytes = Buffer.byteLength(output, "utf-8");
  const lines = output.split("\n");
  if (totalBytes <= MAX_TOOL_BYTES && lines.length <= MAX_TOOL_LINES) return output;

  // Never cut mid-line: keep whole lines until either budget is spent. An
  // AX-tree snapshot is line-oriented, and half a node is worse than one fewer.
  const kept: string[] = [];
  let used = 0;
  for (const line of lines.slice(0, MAX_TOOL_LINES)) {
    const size = Buffer.byteLength(line, "utf-8") + 1;
    if (used + size > MAX_TOOL_BYTES) break;
    kept.push(line);
    used += size;
  }
  const head = kept.join("\n");

  let note = `[Output truncated: ${kept.length} of ${lines.length} lines (${humanSize(used)} of ${humanSize(totalBytes)}).`;
  try {
    const dir = mkdtempSync(join(tmpdir(), `pi-stealth-${prefix}-`));
    const file = join(dir, "output.txt");
    writeFileSync(file, output, "utf-8");
    note += ` Full output saved to ${file.replace(/\\/g, "/")} — read that file if you need the rest.]`;
  } catch {
    // The spill file is a convenience, not a correctness requirement: if the
    // temp dir is unwritable the excerpt is still strictly better than 80KB.
    note += " Full output could not be saved to disk.]";
  }
  return `${head}\n\n${note}`;
}
