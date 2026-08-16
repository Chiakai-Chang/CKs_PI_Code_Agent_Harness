/**
 * Task-Shape Router — hand the model a routine at the moment it skips one.
 *
 * The harness owner's report: ask Pi for a market survey and it opens web_search
 * a dozen times and reports back, while Superpowers, planning-with-files,
 * MECE-Autopilot and C.A.S.E. sit installed. Measured with
 * scripts/measure-triggers.py (local model, isolated sessions, neutral cwd):
 *
 *   debug-methodology         2/3   67%
 *   multi-step-methodology    0/3    0%
 *
 * It is not reachability. Dumping the real system prompt shows all 21 core
 * methodology skills present with their descriptions, 39,980 chars. Debugging
 * fires because the request lands in systematic-debugging's vocabulary; a market
 * survey lands in nobody's, and those descriptions live in submodules.
 *
 * Routine (arXiv 2507.14447) took Qwen3-14B from 32.6% to 83.3% on multi-step
 * tool calling by handing the model a structured script instead of asking it to
 * pick from a list. This harness already hands it a 122-entry catalogue at
 * session start; what it has never had is a concrete script at the moment it
 * reaches for the shortcut.
 *
 * Advises, never blocks. Under `pi --print` there is nobody to approve a hard
 * stop, and GateGuard taught this repo what happens when a gate nobody has ever
 * run goes live: it denied the first bash command of every session.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";

import { fileURLToPath } from "node:url";
import { classifyRequest, buildRoutine, buildSystemPromptNote, buildKindNote, isBroadTool } from "./shape.ts";
import { hasAnyPlan, isCaseProject } from "./plan.ts";
import { GoalRestate, MAX_RESTATEMENTS, RESTATE_THRESHOLD } from "./goal-restate.ts";
import { calibrated } from "./calibration.ts";

// import.meta.url, not require.resolve: Pi shims `require`, bare node does not,
// and every config read here is wrapped in a catch that returns the DEFAULT — so
// each switch reported ON regardless of harness-config.json outside Pi. That
// invalidated the first A/B on 2026-08-16 (both arms identical).
const pkgPath = join(dirname(fileURLToPath(import.meta.url)), "package.json");
const pkg = JSON.parse(readFileSync(pkgPath, "utf-8"));
const HARNESS_ROOT = pkg["pi-harness"]?.root || join(dirname(pkgPath), "../..");

/** Label the block so it is never mistaken for what the tool printed. */
const HEADER = "[task-shape] routing note (not command output):";

/**
 * A harness-config boolean, defaulting to on and failing open.
 *
 * Both flags read through here are on by default, unlike `enableEccGateGuard`.
 * The difference is deliberate: that one blocks, these only add a sentence. A
 * guard that has never run should not go live by accident; a note can.
 */
function flagOn(harnessRoot: string, key: string): boolean {
  try {
    const cfgPath = join(harnessRoot, "pi-config", "harness-config.json");
    if (!existsSync(cfgPath)) return true;
    return JSON.parse(readFileSync(cfgPath, "utf8"))[key] !== false;
  } catch {
    return true;
  }
}

export default function (pi: ExtensionAPI) {
  const enabled = flagOn(HARNESS_ROOT, "enableTaskShapeRouter");
  /**
   * Separate from the router flag so the restatement can be measured alone.
   *
   * This exists because of the measurement, not in spite of it: an A/B that
   * switches `enableTaskShapeRouter` turns off the routing note as well, and
   * would attribute both effects to one cause. The requirement surfaced while
   * designing the drift scenario, which is the argument for designing the
   * measurement before believing the mechanism.
   */
  const restateOn = enabled && flagOn(HARNESS_ROOT, "enableGoalRestate");

  // Armed by a multi-step request, spent on the first broad tool call, and
  // reset per session — Pi calls the default export once per process but fires
  // session_start once per session.
  let armed: string | null = null;
  let pending: string | null = null;
  let delivered = 0;
  // When this session began. `hasAnyPlan` compares the plan's mtime against it,
  // so a plan from a previous week no longer counts as "already planning".
  let sessionStartedAt = Date.now();

  /**
   * How many times the routine may ride along on a tool result in one session.
   *
   * The first version stopped after one, permanently, for the whole session. In
   * session 019fd29d that was measured costing everything: three user turns, the
   * note delivered on turn 1, and turns 2 and 3 — where the request was
   * *sharpened* and the work actually mattered — routed by nobody. Thirty-eight
   * searches, two pages read, no file written.
   *
   * A conversation is not one request. Each new turn gets classified again; the
   * cap only stops a single long turn from repeating itself.
   */
  const MAX_DELIVERIES = 2;

  // Mid-run goal restatement. Separate state from the routing note above: the
  // note is spent on the first broad tool call, this one arms for the whole
  // cycle and fires deep into it. See goal-restate.ts for why it exists.
  const restate = new GoalRestate(
    calibrated(HARNESS_ROOT, "goalRestateThreshold", RESTATE_THRESHOLD),
    calibrated(HARNESS_ROOT, "goalRestateMax", MAX_RESTATEMENTS),
  );

  pi.on("session_start", async () => {
    armed = null;
    pending = null;
    delivered = 0;
    sessionStartedAt = Date.now();
    restate.reset();
  });

  pi.on("before_agent_start", (event, ctx) => {
    if (!enabled) return;
    try {
      const shape = classifyRequest(event.prompt);
      // T-A3. In a C.A.S.E. project the restatement stands down: case-bridge
      // restates the claimed task's Local DoD instead, which is the goal there.
      // This one quotes the USER's request, and the real request for a queue
      // run is 「請處理 02_Task_Queue 裡待辦的任務」 — it names no goal, and it
      // classifies as single-step, so this has never armed in a C.A.S.E. run
      // anyway. Standing down explicitly is the difference between a mechanism
      // that is off and one that is off by accident.
      const caseProject = isCaseProject(ctx.cwd);
      // Armed before the plan check below returns: a project that already has a
      // plan still forgets its goal by step 18 — that is the failure this
      // addresses, and it is independent of whether a plan file exists.
      if (restateOn && !caseProject) restate.begin(event.prompt, shape.multiStep === true);
      // A single-step request can still be a KIND of work with a methodology
      // skill behind it, and that is where the measured zero lives: debugging
      // asks are short and singular, so they never reach the multi-step branch
      // below. Measured over 121 real prompts — multi-step 19%, kind 13%, both
      // 5% — so riding the kind sentence on the multi-step note would have left
      // `systematic-debugging` at the 0/165 sessions this change exists to fix.
      // The C.A.S.E. stand-down still applies: there the task package names the
      // methodology.
      if (!shape.multiStep) {
        if (caseProject) return;
        const kindNote = buildKindNote(event.prompt);
        if (kindNote) return { systemPrompt: `${event.systemPrompt ?? ""}

${kindNote}` };
        return;
      }
      // A C.A.S.E. project plans inside the task package and has a gate that
      // enforces it. The routine below would point at task_plan.md, which
      // nothing there reads. Stand down and let the task-local constitution
      // carry the planning and the methodology — see plan.ts::isCaseProject.
      if (caseProject) return;
      // A project that already has a plan does not need to be told to make one.
      if (hasAnyPlan(ctx.cwd, sessionStartedAt)) return;
      armed = buildRoutine(shape, event.prompt);

      // Delivered here as well as on the tool result, because the first design
      // delivered only there and was measured failing: the routine arrived in
      // the first web_search's result and the model ignored it across 17 tool
      // calls. A tool_call handler cannot add text without blocking, so that
      // path is always *after* the model has committed. Models attend to the
      // start and the end of a context, and an instruction that matters belongs
      // in more than one place.
      // `hasUI` is documented as "whether dialog-capable UI is available (true in
      // TUI and RPC modes)". Under `pi --print` there is nobody to answer a
      // scoping question, and one measured run spent its whole turn asking four.
      const note = buildSystemPromptNote(shape, {
        interactive: ctx.hasUI !== false, prompt: event.prompt });
      if (note) return { systemPrompt: `${event.systemPrompt ?? ""}\n\n${note}` };
    } catch {
      // Classification must never break a turn. Disarm rather than leave the
      // previous cycle's goal in place — a stale restatement quoting a request
      // the user has already moved on from is worse than none.
      restate.reset();
    }
  });

  pi.on("tool_call", async (event, ctx) => {
    if (!armed || !isBroadTool(event.toolName)) return;
    if (delivered >= MAX_DELIVERIES) {
      armed = null;
      return;
    }
    pending = armed;
    armed = null;
    delivered++;
    ctx.ui.notify("🧭 多步任務:已提示先規劃再執行", "info");
    // No block. The routine says what to do; the model decides — and when it
    // decides not to, `yes-hooks-bridge`'s depth and artifact gates are what
    // actually stops the run. This bridge advises; that one refuses.
  });

  pi.on("tool_result", async (event) => {
    // Both riders share one channel, so they are collected into one return.
    // Returning early on the first would have silently starved the second, and
    // an injection that never reaches the model is this repo's most repeated
    // defect.
    const blocks: string[] = [];
    if (pending) {
      blocks.push(`${HEADER}\n${pending}`);
      pending = null;
    }
    // `isError` is declared on ToolResultEventBase and is not optional, so it
    // needs no cast and no fallback.
    const goal = restateOn ? restate.afterToolResult(event.isError) : null;
    if (goal) blocks.push(goal);
    if (!blocks.length) return;
    const existing = Array.isArray(event.content) ? [...event.content] : [];
    return {
      content: [...existing, ...blocks.map((text) => ({ type: "text" as const, text }))],
    };
  });
}
