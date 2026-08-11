/**
 * Numbers that belong to the model, read from the harness config.
 *
 * T-A2. `RESTATE_THRESHOLD = 12` and `MAX_RESTATEMENTS = 2` were measured
 * against one model on one day. Left as constants in the bridge they swap
 * models in silence: no error, just a reminder arriving too late or too often.
 * Harness-Bench (arXiv 2605.27922) is the general form — capability belongs to
 * the model–harness configuration, so the numbers calibrated to a configuration
 * belong where the configuration is declared.
 *
 * This lives in its own file rather than inside `index.ts` because `index.ts`
 * opens with `require.resolve("./package.json")`, and `require` exists only
 * under Pi's shim. A test driving the reader through the bridge entry point
 * dies at import with "require is not defined in ES module scope" — the reader
 * would then be covered by nothing, which is how a dead guard survived 1287
 * tests earlier the same day.
 */

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

/**
 * A calibrated integer from the global config, or the caller's fallback.
 *
 * Unreadable config means "use the shipped value", never zero — the same
 * fail-open direction as `flagOn`. The type test is strict on purpose: a config
 * saying `"12"` is supplying text, `0` would restate after every single tool
 * result, and coercing either here would be the config layer guessing.
 */
export function calibrated(harnessRoot: string, key: string, fallback: number): number {
  try {
    const cfgPath = join(harnessRoot, "pi-config", "harness-config.json");
    if (!existsSync(cfgPath)) return fallback;
    const v = JSON.parse(readFileSync(cfgPath, "utf8"))[key];
    // `typeof true === "boolean"` in JS, but `Number.isInteger(true)` is false,
    // so booleans fall through to the fallback rather than becoming 1.
    return typeof v === "number" && Number.isInteger(v) && v > 0 ? v : fallback;
  } catch {
    return fallback;
  }
}
