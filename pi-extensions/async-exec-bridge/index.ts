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
import { Type } from "typebox";
import { randomBytes } from "node:crypto";
import { readFileSync } from "node:fs";
import { ENVELOPE_TAIL_BYTES, JOB_TIMEOUT_MS } from "./constants.ts";
import { buildEnvelope, tailBytes } from "./envelope.ts";
import { readJobs, reconcile, writeJob, type JobRecord, type LocalModel } from "./jobs.ts";
import { outFile } from "./paths.ts";
import { preflight } from "./preflight.ts";
import { readLease, release } from "./lease.ts";
import { isAlive, killTree, readExitCode, startDetached } from "./spawn.ts";
import { stateBlock } from "./state-block.ts";

export default function (pi: ExtensionAPI) {
  let dead = false;
  const timers = new Set<NodeJS.Timeout>();
  /** Completions that finished while a wake was already in flight. They ride
   *  along in the next envelope instead of each triggering a competing turn. */
  let coalescing: JobRecord[] = [];
  let wakePending = false;

  function envelopeFor(jobs: JobRecord[]): string {
    const tails = new Map<string, string>();
    for (const j of jobs) {
      try {
        tails.set(j.id, tailBytes(readFileSync(j.outPath, "utf-8"), ENVELOPE_TAIL_BYTES));
      } catch {
        // No output captured.
      }
    }
    return buildEnvelope(jobs, tails);
  }

  function wake(cwd: string, ctx: any) {
    const batch = coalescing;
    coalescing = [];
    if (batch.length === 0) {
      wakePending = false;
      return;
    }
    for (const j of batch) writeJob(cwd, { ...j, acknowledged: true });
    // Only ask Pi to start a turn when it is actually idle. Mid-run, followUp
    // alone delivers once it settles; adding triggerTurn would race the turn
    // already in progress.
    const idle = ctx?.isIdle?.() !== false;
    pi.sendMessage(
      { customType: "async-exec", content: envelopeFor(batch), display: true },
      { deliverAs: "followUp", triggerTurn: idle },
    );
    wakePending = false;
  }

  function finish(
    cwd: string,
    ctx: any,
    job: JobRecord,
    state: JobRecord["state"],
    exitCode: number | null,
  ) {
    // State first, always: waking can fail and be retried, state cannot.
    const done: JobRecord = { ...job, state, exitCode, endedAt: Date.now() };
    writeJob(cwd, done);
    release(cwd, job.id);
    if (dead) return;
    coalescing.push(done);
    if (wakePending) return;
    wakePending = true;
    // One tick of slack so simultaneous completions land in a single envelope.
    const t = setTimeout(() => {
      timers.delete(t);
      wake(cwd, ctx);
    }, 250);
    timers.add(t);
  }

  const text = (s: string) => ({ content: [{ type: "text" as const, text: s }] });

  pi.registerTool({
    name: "bg_start",
    label: "Background Start",
    description:
      "Start a long-running command in the background and return immediately. " +
      "You will be woken with the result when it finishes.",
    promptSnippet:
      "bg_start(cmd, label?, localModel?): run a long command in the background; you are woken when it finishes.",
    promptGuidelines: [
      "For a command that will take minutes (builds, full test suites, benchmarks), call bg_start instead of bash — bash blocks this turn until it returns.",
      "After bg_start, decide PARK or CONTINUE in one line. PARK just means issuing no further tool calls this turn; there is no park tool to call.",
      "Use bg_status to check on work you dispatched, and bg_cancel to stop it. A background job keeps running even if this turn is interrupted.",
    ],
    parameters: Type.Object({
      cmd: Type.String({ description: "The shell command to run, e.g. 'npm test'" }),
      label: Type.Optional(Type.String({ description: "Short human-readable name for this job" })),
      localModel: Type.Optional(
        Type.Union([Type.Literal("none"), Type.Literal("shared"), Type.Literal("exclusive")], {
          description:
            "Whether this job touches the local model server: none (default), shared (uses the running server), exclusive (needs to load its own model — refused in v1)",
        }),
      ),
    }),
    async execute(_id, params: any, _signal, _onUpdate, ctx: any) {
      const args = params as { cmd: string; label?: string; localModel?: LocalModel };
      const cwd: string = ctx.cwd;
      const localModel: LocalModel = args.localModel ?? "none";
      // v1 has no live GPU probe, so the residency check cannot be honest.
      // Refuse outright rather than pretend to have checked — a wrong "yes"
      // here means two large models racing for memory.
      if (localModel === "exclusive") {
        return text(
          '[async-exec] refused: localModel "exclusive" is not supported yet — ' +
            "v1 has no live GPU residency probe, so it cannot verify a second model would fit. " +
            'Use "shared" to reuse the running server, or use a cloud model.',
        );
      }
      const jobs = readJobs(cwd);
      // No GPU figures are passed: v1 has no probe. preflight treats their
      // absence as "cannot verify" and refuses exclusive on its own, so the
      // early return above is a clearer duplicate of that gate, not its only
      // enforcement.
      const gate = preflight({
        jobs,
        cmd: args.cmd,
        cwd,
        localModel,
        leaseHeld: readLease(cwd) !== null,
      });
      if (gate.ok === false) return text(`[async-exec] refused: ${gate.reason}`);
      if (gate.ok === "duplicate") return text(`[async-exec] already running as job ${gate.id}`);

      const id = randomBytes(2).toString("hex");
      const out = outFile(cwd, id);
      const rc = `${out}.rc`;
      const pid = startDetached(args.cmd, cwd, out, rc);
      if (pid === null) return text("[async-exec] refused: could not start the process");

      const job: JobRecord = {
        id, label: args.label ?? args.cmd, cmd: args.cmd, cwd, localModel,
        pid, state: "running", startedAt: Date.now(), endedAt: null,
        exitCode: null, outPath: out, acknowledged: false,
      };
      writeJob(cwd, job);

      const poll = setInterval(() => {
        if (dead) return;
        if (isAlive(pid)) {
          if (Date.now() - job.startedAt > JOB_TIMEOUT_MS) {
            killTree(pid);
            clearInterval(poll);
            timers.delete(poll);
            finish(cwd, ctx, job, "timeout", null);
          }
          return;
        }
        clearInterval(poll);
        timers.delete(poll);
        // The pid is gone; the shell wrapper's .rc file is the only witness to
        // how it went. A missing code means it never finished cleanly.
        const code = readExitCode(rc);
        finish(cwd, ctx, job, code === 0 ? "done" : "failed", code);
      }, 2000);
      timers.add(poll);

      // Real depth, not a placeholder: the whole point of showing it is to let
      // the model weigh that continuing makes its own next prefill costlier.
      // ContextUsage is { tokens: number | null, contextWindow, percent } —
      // tokens is null right after compaction, before the next LLM response.
      const usage = ctx.getContextUsage?.();
      return text(
        stateBlock({
          dispatched: job,
          running: readJobs(cwd).filter((j) => j.state === "running"),
          // No GPU fields: v1 has no probe, so they are omitted rather than faked.
          contextTokens: usage?.tokens ?? 0,
          // Set PI_MODEL_SERVER_SLOTS in the environment to match the
          // llama-server -np value. Default 1 is the safe reading: it makes the
          // block warn that a shared job blocks rather than merely slows.
          serverSlots: Number(process.env.PI_MODEL_SERVER_SLOTS ?? "1"),
        }),
      );
    },
  });

  pi.registerTool({
    name: "bg_status",
    label: "Background Status",
    description: "List background jobs and their state.",
    promptSnippet: "bg_status(): list background jobs dispatched with bg_start and their state.",
    parameters: Type.Object({}),
    async execute(_id, _params, _signal, _onUpdate, ctx: any) {
      return text(
        readJobs(ctx.cwd)
          .map((j) => `${j.id} · ${j.label} · ${j.state} · exit=${j.exitCode ?? "n/a"}`)
          .join("\n") || "[async-exec] no jobs",
      );
    },
  });

  pi.registerTool({
    name: "bg_cancel",
    label: "Background Cancel",
    description: "Cancel a running background job by id.",
    promptSnippet: "bg_cancel(id): stop a background job and its whole process tree.",
    parameters: Type.Object({
      id: Type.String({ description: "The job id returned by bg_start" }),
    }),
    async execute(_id, params: any, _signal, _onUpdate, ctx: any) {
      const job = readJobs(ctx.cwd).find((j) => j.id === params.id);
      if (!job || job.state !== "running") return text(`[async-exec] no running job ${params.id}`);
      if (job.pid !== null) killTree(job.pid);
      writeJob(ctx.cwd, { ...job, state: "cancelled", endedAt: Date.now(), acknowledged: true });
      release(ctx.cwd, job.id);
      return text(`[async-exec] cancelled ${params.id}`);
    },
  });

  pi.on("session_shutdown", async () => {
    dead = true;
    for (const t of timers) clearInterval(t);
    timers.clear();
  });

  // Reconcile only. This handler's result type is undefined — anything returned
  // from session_start is discarded, so the pending envelope cannot be delivered
  // from here. It goes out from before_agent_start below.
  pi.on("session_start", async (_event, ctx: any) => {
    const cwd: string = ctx.cwd;
    for (const j of reconcile(readJobs(cwd), isAlive)) writeJob(cwd, j);
  });

  // The only hook whose result carries a message (BeforeAgentStartEventResult).
  // A job that finished while nothing was listening — a crash, a killed session,
  // a wake that never landed — surfaces here on the next turn. Records are
  // marked acknowledged only once the message is actually being returned, so a
  // failure earlier in this handler leaves the notice on disk for next time.
  pi.on("before_agent_start", async (_event, ctx: any) => {
    if (dead) return;
    const cwd: string = ctx.cwd;
    const pending = readJobs(cwd).filter((j) => j.state !== "running" && !j.acknowledged);
    if (pending.length === 0) return;
    const content = buildEnvelope(pending, new Map());
    for (const j of pending) writeJob(cwd, { ...j, acknowledged: true });
    return { message: { customType: "async-exec", content, display: true } };
  });

  pi.on("agent_settled", async (_event, ctx: any) => {
    const jobs = readJobs(ctx.cwd);
    // Only speak up if this session actually ran background work, and only
    // once nothing is still running — otherwise every ordinary conversation
    // would ping the user.
    const finished = jobs.filter((j) => j.state !== "running");
    if (finished.length === 0) return;
    if (jobs.some((j) => j.state === "running")) return;
    const failed = finished.filter((j) => j.state !== "done").length;
    ctx.ui?.notify?.(
      `[async-exec] ${finished.length} background job(s) finished, ${failed} not clean. Nothing left running.`,
      failed > 0 ? "warning" : "info",
    );
  });
}
