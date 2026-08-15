/**
 * How often the learning-point scan may run, and how often it may speak.
 *
 * Extracted from index.ts because ecc-hooks-bridge cannot be imported under bare
 * node (Pi-only dependencies), so nothing in the suite can drive its handlers —
 * `tests/test_bridge_handlers_run.py` lists it under "not importable". This repo
 * has already paid for that once: an undeclared variable inside a bridge handler
 * survived 774 tests, three checks and a byte-identical install, because
 * importing a module catches syntax errors and not runtime ones. Logic that can
 * be wrong belongs where a test can call it.
 *
 * What it bounds, and why it is a budget rather than a flag.
 *
 * The owner's report was 「📝 偵測到新學習點 (1)。這個一直出現,只有提示沒有意義。」
 * Measured on session 019ffbdd (122 turns, 6.5 hours): the notice had no dedupe
 * while the advisory beside it was already "once", so it fired on every single
 * turn_end, and each firing spawned a python process and walked the whole of
 * ~/.pi/agent/sessions — 20 workspace directories on that machine.
 *
 * The obvious fix, "run once", is wrong in the other direction: a scan on turn
 * two reads a transcript with nothing in it yet, and the reason the original ran
 * every turn was to eventually see a long one. So: a small number of scans,
 * spaced by how much the transcript has actually grown, and exactly one notice.
 */

export class ReflectBudget {
  private runs = 0;
  private lastSize = 0;
  private announced = false;
  private readonly maxRuns: number;
  private readonly growthBytes: number;

  // Plain fields and an explicit assignment, NOT constructor parameter
  // properties (`constructor(private readonly maxRuns = 3)`). Node's native
  // type stripping erases annotations; it does not transform, so that form is
  // `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX` and the module will not load — under
  // Pi, and under the test driver that exists here because this bridge cannot
  // otherwise be driven at all.
  constructor(maxRuns = 3, growthBytes = 20_000) {
    this.maxRuns = maxRuns;
    this.growthBytes = growthBytes;
  }

  /**
   * True when a scan should run now, for a transcript currently `size` bytes.
   * Records the attempt, so a caller that asks twice for the same growth gets
   * one scan — the caller is a turn_end handler and turns are cheap.
   *
   * The first call passes on any size above the threshold, including a session
   * that was resumed and is already large.
   */
  claimScan(size: number): boolean {
    if (!Number.isFinite(size) || size < 0) return false;
    if (this.runs >= this.maxRuns) return false;
    if (size - this.lastSize < this.growthBytes) return false;
    this.lastSize = size;
    this.runs += 1;
    return true;
  }

  /** True the first time only. The notice is for a human watching a TUI; the
   * second one is noise and the hundredth is why nobody reads the first. */
  claimNotice(): boolean {
    if (this.announced) return false;
    this.announced = true;
    return true;
  }

  /** For assertions and for the report file. */
  stats(): { runs: number; lastSize: number; announced: boolean } {
    return { runs: this.runs, lastSize: this.lastSize, announced: this.announced };
  }
}
