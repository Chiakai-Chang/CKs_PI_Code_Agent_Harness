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

import { classifyRequest, buildRoutine, buildSystemPromptNote, isBroadTool } from "./shape.ts";
import { hasAnyPlan } from "./plan.ts";

const pkgPath = require.resolve("./package.json");
const pkg = JSON.parse(readFileSync(pkgPath, "utf-8"));
const HARNESS_ROOT = pkg["pi-harness"]?.root || join(dirname(pkgPath), "../..");

/** Label the block so it is never mistaken for what the tool printed. */
const HEADER = "[task-shape] routing note (not command output):";

/**
 * On by default and fails open, unlike `enableEccGateGuard`.
 *
 * The difference is deliberate: that one blocks, this one only adds a sentence.
 * A guard that has never run should not go live by accident; a note can.
 */
function routerEnabled(harnessRoot: string): boolean {
  try {
    const cfgPath = join(harnessRoot, "pi-config", "harness-config.json");
    if (!existsSync(cfgPath)) return true;
    return JSON.parse(readFileSync(cfgPath, "utf8"))["enableTaskShapeRouter"] !== false;
  } catch {
    return true;
  }
}

export default function (pi: ExtensionAPI) {
  const enabled = routerEnabled(HARNESS_ROOT);

  // Armed by a multi-step request, spent on the first broad tool call, and
  // reset per session — Pi calls the default export once per process but fires
  // session_start once per session.
  let armed: string | null = null;
  let pending: string | null = null;
  let firedThisSession = false;

  pi.on("session_start", async () => {
    armed = null;
    pending = null;
    firedThisSession = false;
  });

  pi.on("before_agent_start", (event, ctx) => {
    if (!enabled || firedThisSession) return;
    try {
      const shape = classifyRequest(event.prompt);
      if (!shape.multiStep) return;
      // A project that already has a plan does not need to be told to make one.
      if (hasAnyPlan(ctx.cwd)) return;
      armed = buildRoutine(shape);

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
      const note = buildSystemPromptNote(shape, { interactive: ctx.hasUI !== false });
      if (note) return { systemPrompt: `${event.systemPrompt ?? ""}\n\n${note}` };
    } catch {
      // Classification must never break a turn.
    }
  });

  pi.on("tool_call", async (event, ctx) => {
    if (!armed || !isBroadTool(event.toolName)) return;
    pending = armed;
    armed = null;
    firedThisSession = true;
    ctx.ui.notify("🧭 多步任務:已提示先規劃再執行", "info");
    // No block. The routine says what to do; the model decides.
  });

  pi.on("tool_result", async (event) => {
    if (!pending) return;
    const text = `${HEADER}\n${pending}`;
    pending = null;
    const existing = Array.isArray(event.content) ? [...event.content] : [];
    return { content: [...existing, { type: "text" as const, text }] };
  });
}
