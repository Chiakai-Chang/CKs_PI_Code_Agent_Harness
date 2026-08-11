/**
 * Numbers calibrated to the model, read from the harness config (T-A2).
 *
 * A second copy of `task-shape-bridge/calibration.ts`, and deliberately so:
 * bridges are installed as independent directories, so one importing another's
 * file would break the moment either is installed alone. What must NOT drift is
 * the contract, and this repo has the scar for exactly that — `uninstall.py`
 * managed five bridges while `restore.py` managed eleven, and seven kept loading
 * forever. `tests/test_calibration_layer.py` drives BOTH copies against the same
 * fixtures, so a change to one that is not made to the other turns a test red.
 *
 * It lives outside `index.ts` because that file opens with
 * `require.resolve("./package.json")`, and `require` exists only under Pi's
 * shim: a test importing the bridge entry point from node dies before its first
 * assertion, and the reader would be covered by nothing.
 */

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

/**
 * A calibrated integer from the global config, or the caller's fallback.
 *
 * Strict on type on purpose: `"12"` is text, and `0` would restate after every
 * single tool result. An unreadable config means "use the shipped value".
 */
export function calibratedNumber(harnessRoot: string, key: string, fallback: number): number {
  try {
    const cfgPath = join(harnessRoot, "pi-config", "harness-config.json");
    if (!existsSync(cfgPath)) return fallback;
    const v = JSON.parse(readFileSync(cfgPath, "utf8"))[key];
    // `Number.isInteger(true)` is false, so booleans fall through rather than
    // becoming 1.
    return typeof v === "number" && Number.isInteger(v) && v > 0 ? v : fallback;
  } catch {
    return fallback;
  }
}
