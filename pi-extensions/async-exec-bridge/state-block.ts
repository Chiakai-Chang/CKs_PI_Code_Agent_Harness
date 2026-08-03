import type { JobRecord } from "./jobs.ts";

export interface StateInput {
  dispatched: JobRecord;
  running: JobRecord[];
  /** Omit when there is no live probe. Printing a placeholder would tell the
   *  model it has 93 GiB of headroom while a resident model is using 85 - and
   *  feeding the deliberation fabricated facts is worse than feeding it none. */
  gpuCommittedGiB?: number;
  carveGiB?: number;
  contextTokens: number;
  /** llama-server slot count. At 1, a "shared" job serialises at the server:
   *  the agent's own decode stops rather than merely slowing. */
  serverSlots: number;
}

export function stateBlock(i: StateInput): string {
  const d = i.dispatched;
  const depthK = `${Math.round(i.contextTokens / 1000)}K`;

  const lines = [
    `[bg] dispatched job ${d.id} · "${d.label}" · localModel=${d.localModel}`,
  ];
  if (i.gpuCommittedGiB !== undefined && i.carveGiB !== undefined) {
    const headroom = (i.carveGiB - i.gpuCommittedGiB).toFixed(1);
    lines.push(
      `[bg] running: ${i.running.length}    GPU committed: ${i.gpuCommittedGiB.toFixed(1)} GiB / ${i.carveGiB} GiB carve (headroom ${headroom} GiB)`,
    );
  } else {
    lines.push(`[bg] running: ${i.running.length}    GPU state: not probed in v1`);
  }
  lines.push(
    `[bg] your context depth: ~${depthK} — prefill and decode both get slower as this grows`,
  );

  if (d.localModel === "shared") {
    lines.push(
      i.serverSlots <= 1
        ? `[bg] WARNING: the model server has ${i.serverSlots} slot, so this job will BLOCK your own decode until it finishes, not merely slow it`
        : `[bg] note: this job shares the model server (${i.serverSlots} slots), so it will slow your own decode`,
    );
  }

  lines.push(
    "Decide in one line: PARK (stop issuing tool calls and end this turn; you will be woken when the job finishes) or CONTINUE (say what you will do meanwhile).",
  );
  return lines.join("\n");
}
