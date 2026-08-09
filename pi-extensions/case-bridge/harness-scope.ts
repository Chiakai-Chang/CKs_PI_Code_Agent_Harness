/**
 * A flag that belongs to one project, resolved without disturbing the others.
 *
 * `pi-config/harness-config.json` is global, and seven bridges read it from ten
 * call sites. Measured 2026-08-08: re-measuring the advancer meant switching
 * `enableCaseAdvancer` on globally and running restore, so for the three
 * minutes of that measurement any other C.A.S.E. project the user opened would
 * have been driven too. Task_002's output.md listed the limitation
 * ("無法讓旗標只對 fixture 生效") and it stayed open.
 *
 * `research/prime-agent` keeps continual-harness state local by default and
 * promotes only durable cross-session lessons to global (refinement.ts:974).
 * The default direction is adopted; the location is not — theirs is per
 * session, and a measurement runs in a different directory under a different
 * session, so this is per project.
 *
 * Two properties matter more than the feature:
 *
 * 1. **No local file must behave exactly as before.** `enableCaseAdvancer`
 *    triggers turns, and every machine today has no local file. Drift in the
 *    open direction would start the harness driving sessions nobody asked for.
 * 2. **The local file is a trust boundary.** It ships with the project being
 *    worked on, which is not necessarily the user's own code, so exactly one
 *    named flag is readable from there. A local file that could switch on deep
 *    research or switch a guard off would make config an attack surface.
 */

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

/** The local file a project may carry. */
export const LOCAL_CONFIG_NAME = ".pi-harness.json";

/**
 * Flags a project may set for itself.
 *
 * Deliberately one entry. Widening this is a decision taken one flag at a time
 * with a reason, never a side effect of touching this file — the other
 * nineteen have no measured problem, and switching seven bridges' behaviour at
 * once leaves nobody able to say which one broke.
 */
export const PROJECT_SCOPED: ReadonlySet<string> = new Set([
  "enableCaseAdvancer",
  // Lets an experiment raise the CLAIM exit ramp inside its own fixture
  // instead of editing a shipped constant. The 2026-08-09 budget experiment
  // edited the constant and relied on remembering to revert it; remembering is
  // not a mechanism.
  "caseClaimRefusalTurns",
]);

/**
 * Numeric settings a project may set, and the band it may set them within.
 *
 * The direction is the whole safeguard. The file arrives with the project
 * being worked on, so a project that could set `caseClaimRefusalTurns` to 1
 * would make the gate stand aside after a single turn — switching a guard off
 * through the config door. Tighter is allowed, looser is not, and the upper
 * bound exists because a gate that never lets go locks a model that cannot
 * work out how to claim, which is the failure the exit ramp prevents.
 */
const NUMERIC_BOUNDS: Record<string, { min: number; max: number }> = {
  caseClaimRefusalTurns: { min: 8, max: 12 },   // min tracks the shipped default
};

function withinBounds(key: string, value: unknown): boolean {
  const bounds = NUMERIC_BOUNDS[key];
  if (!bounds) return true;
  // `typeof true === "boolean"`, and a numeric string is not a number: a
  // project supplying "8" is supplying text, and coercing it here would be the
  // config layer guessing.
  if (typeof value !== "number" || !Number.isInteger(value)) return false;
  return value >= bounds.min && value <= bounds.max;
}

function readJsonObject(path: string): Record<string, unknown> | null {
  try {
    if (!existsSync(path)) return null;
    const data = JSON.parse(readFileSync(path, "utf8"));
    // An array parses as JSON and is not a config. Treating it as one would
    // read `undefined` for every key, which is indistinguishable from "not
    // configured" and hides the mistake.
    return data && typeof data === "object" && !Array.isArray(data)
      ? (data as Record<string, unknown>)
      : null;
  } catch {
    // Unreadable local state means "no local state", never "everything off".
    // A broken file in someone's project must not disable the harness.
    return null;
  }
}

/**
 * The value of a flag for this project, or undefined when nothing sets it.
 *
 * Undefined rather than false on purpose: the caller owns the default, and
 * turning "not configured" into "switched on" here would be the one mistake
 * this module cannot afford.
 */
export function resolveFlag(
  name: unknown,
  cwd: unknown,
  harnessRoot: unknown,
): unknown {
  const key = String(name ?? "");
  if (!key) return undefined;

  const project = String(cwd ?? "");
  if (project && PROJECT_SCOPED.has(key)) {
    const local = readJsonObject(join(project, LOCAL_CONFIG_NAME));
    if (local && key in local && withinBounds(key, local[key])) return local[key];
  }

  const root = String(harnessRoot ?? "");
  if (!root) return undefined;
  const global = readJsonObject(join(root, "pi-config", "harness-config.json"));
  if (global && key in global) return global[key];
  return undefined;
}

/**
 * The scoped flags as they stood when the session began.
 *
 * Taken from the-last-harness, which snapshots its experimental flags at
 * session start or an explicit reload so that toggling one does not change a
 * running session. Ours read the file on every call, which has two costs and
 * the second is the expensive one:
 *
 *  1. editing `.pi-harness.json` mid-run changes behaviour immediately;
 *  2. "which configuration did this run use" is not a question the record can
 *     answer afterwards.
 *
 * Three measurement rounds this week were invalidated by the environment
 * rather than the harness, so a run that cannot state its own configuration is
 * a run whose numbers have to be argued about.
 */
export class ScopeSnapshot {
  // No `taken` flag: the mutation sweep showed it could be initialised either
  // way with nothing observable, because an unread snapshot and a reset one are
  // both empty maps and `get` returns undefined from both. A field whose value
  // cannot change any answer is weight, not state.
  private values = new Map<string, unknown>();

  /** Read every project-scoped flag once, at a session boundary. */
  take(cwd: unknown, harnessRoot: unknown): void {
    this.values.clear();
    for (const key of PROJECT_SCOPED) {
      const v = resolveFlag(key, cwd, harnessRoot);
      if (v !== undefined) this.values.set(key, v);
    }
  }

  /**
   * The session's answer, or undefined when no snapshot has been taken.
   *
   * Undefined rather than a default on purpose: answering `false` before
   * `session_start` would make "not yet read" indistinguishable from "switched
   * off", and the flag this mostly guards is the one that triggers turns.
   */
  get(key: string): unknown {
    return this.values.get(key);
  }

  /** A short, stable identifier for the configuration this session is running. */
  digest(): string {
    const body = JSON.stringify([...this.values.entries()].sort());
    let h = 0;
    for (let i = 0; i < body.length; i++) h = (Math.imul(31, h) + body.charCodeAt(i)) | 0;
    return `scope:${(h >>> 0).toString(16).padStart(8, "0")}:${this.values.size}`;
  }

  reset(): void {
    this.values.clear();
  }
}
