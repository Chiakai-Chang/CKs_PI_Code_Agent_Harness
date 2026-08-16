#!/usr/bin/env python3
"""Break the guards mechanically and require something to turn red.

Usage:
    python scripts/check-guard-mutations.py                # sampled, all modules
    python scripts/check-guard-mutations.py --all          # exhaustive (slow)
    python scripts/check-guard-mutations.py --only harness-root.ts
    python scripts/check-guard-mutations.py --cap 20

Four defects of one class are on record, and every one was a check that could
not fail: a break fixture using a command the extractor does not recognise, a
fixture whose broken and correct versions returned the same answer, a guard with
twelve green tests that had never fired, and an e2e printing PASS while
measuring nothing. The 2026-08-06 retrospective named the class and recorded
that it had discipline and no mechanism; on 2026-08-08 the discipline failed
again, and Task_003's five deliberate breaks produced three catches.

`research/metaharness` ADR-010 declined mutation testing in v1.0 because "the
perf cost on a large test suite is significant", and named the condition for
reversing that: "if we measure that it would have caught real bugs." Those four
are the measurement. The cost objection is answered by scope rather than
ignored — seven guard modules, each running only its own test modules, stopping
at the first red, sampled by default.

`research/pi-tool-repair-layer` sets mutation-score targets per path tier
(critical 70%, standard 50%). The tiering is adopted as "guard modules only";
the percentage is not. A percentage tells you how much evasion is affordable,
and this repo has already measured what a threshold does to behaviour. Every
survivor must instead be named in the allowlist with an argument for why it is
untestable, or the run fails.

Not wired into CI: it needs node and minutes. CI runs this script's own unit
tests, including the one that plants a module with no real assertions and
requires the runner to report survivors — because a mutation runner that always
reports a clean sweep is the fifth instance of the class it was built to end.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import subprocess
import signal
import sys
from collections import namedtuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWLIST = os.path.join(ROOT, "scripts", "guard-mutation-allowlist.json")
DEFAULT_CAP = 14

# Declared, never derived. Deriving it by grepping the test files for a module
# name was wrong on the first module tried: tests/test_installed_drift.py names
# harness-root.ts in its docstring and asserts nothing about it. A mutation
# scored against the wrong test module is a result with no meaning.
GUARD_MODULES = {
    # The C.A.S.E. adapter's modules are NOT here. They moved to the protocol's
    # own repository on 2026-08-17 (adapters/pi/case-bridge) together with their
    # tests and a CI workflow, so C.A.S.E. can be adopted without a harness
    # owning it. Sweeping them from here would mutate a submodule's source,
    # which is another repository's working tree.
    #
    # OPEN, and recorded rather than assumed away: that repo has no mutation
    # sweep of its own yet, so those eight modules are currently unswept. Filed
    # in PROGRESS.md.

    "pi-extensions/yes-hooks-bridge/bash-containment.ts": ["test_bash_containment"],
    "pi-extensions/yes-hooks-bridge/blocked-claim.ts": ["test_blocked_claim", "test_blocked_claim_channel", "test_blocked_claim_vocabulary"],
    "pi-extensions/yes-hooks-bridge/research-depth.ts": ["test_research_depth", "test_research_depth_bash"],
    "pi-extensions/yes-hooks-bridge/harness-root.ts": ["test_harness_root_redirect"],
    "pi-extensions/yes-hooks-bridge/loop-detect.ts": ["test_cycle_guard"],
    "pi-extensions/yes-hooks-bridge/compaction-echo.ts": ["test_compaction_echo"],
    # Repairs tool arguments in place rather than refusing, so a weakened
    # predicate here does not fail loudly the way a dead guard does — it just
    # quietly stops stripping, or starts stripping honest markup out of files
    # the agent writes. Both directions are asserted in test_dialect_residue.
    "pi-extensions/yes-hooks-bridge/dialect-residue.ts": ["test_dialect_residue"],
    # Bounds how often the learning-point scan runs and speaks. Weakening either
    # bound restores the failure the owner reported — a notice on every one of
    # 122 turns — and nothing else in the suite can reach it, because
    # ecc-hooks-bridge is not importable under bare node.
    "pi-extensions/ecc-hooks-bridge/reflect-budget.ts": ["test_reflect_budget"],
    # The only mechanism aimed at the owner's stated complaint. A weakened
    # threshold or a widened exemption turns it back into what the rest of the
    # planning bridge already was: something that only helps sessions that
    # already plan.
    "pi-extensions/planning-with-files-bridge/no-plan-gate.ts": ["test_no_plan_gate"],
    "pi-extensions/task-shape-bridge/goal-restate.ts": ["test_goal_restate"],
    # Added 2026-08-10 after measuring coverage: 33 of 48 pure modules were
    # never swept, and these two sit directly in the decision path this week's
    # work depends on — `shape.ts` decides multi-step, `plan.ts` decides whether
    # the router stands down in a C.A.S.E. project. Every weak assertion found
    # today was found by this sweep and none by reading assertion styles, so
    # coverage of the sweep is the lever, not the wording of the tests.
    "pi-extensions/task-shape-bridge/shape.ts": ["test_task_shape"],
    "pi-extensions/task-shape-bridge/plan.ts": ["test_plan_module", "test_stale_plan_does_not_silence"],
    # T1b batch 1, added 2026-08-12: the three modules written or rewritten that
    # day. Fresh code with fresh tests is where a weak assertion is most likely
    # and least likely to have been noticed — two of the three exist only because
    # `index.ts` cannot be imported by a test, which is the same reason nothing
    # was covering them yesterday.
    "pi-extensions/task-shape-bridge/calibration.ts": ["test_calibration_layer", "test_goal_restate"],
    "pi-extensions/mece-autopilot-bridge/notice.ts": ["test_mece_notice"],
    # T1b batch 2, added 2026-08-12: every remaining pure module that a python
    # test can drive. What is left after this is async-exec-bridge/*, whose tests
    # are bun `.test.ts` files this scanner cannot run — recorded as an exclusion
    # with a reason rather than left looking unswept.
    "pi-extensions/ecc-hooks-bridge/advisory.ts": ["test_ecc_hooks_bridge"],
    "pi-extensions/ecc-hooks-bridge/ecc-payload.ts": ["test_ecc_payload", "test_ecc_hook_contract"],
    "pi-extensions/ecc-hooks-bridge/plan.ts": ["test_plan_detection_parity"],
    "pi-extensions/stealth-web-bridge/readability.ts": ["test_readability"],
    "pi-extensions/stealth-web-bridge/truncate.ts": ["test_stealth_web_bridge"],
    "pi-extensions/deep-research-bridge/research.ts": ["test_deep_research_bridge"],
}

# Pure modules this scanner deliberately does NOT sweep, and why. Written down
# rather than left implicit: T1b started because 33 of 48 modules were unswept
# and nothing said so — an unguarded list drifts, which is how `uninstall.py`
# came to manage five bridges while `restore.py` managed eleven.
#
# `tests/test_mutation_coverage.py` requires every pure module to be in exactly
# one of GUARD_MODULES or this dict, so a new module cannot arrive unnoticed.
UNSWEPT_WITH_REASON = {
    "pi-extensions/async-exec-bridge/capture.ts": "bun",
    "pi-extensions/async-exec-bridge/constants.ts": "bun",
    "pi-extensions/async-exec-bridge/envelope.ts": "bun",
    "pi-extensions/async-exec-bridge/jobs.ts": "bun",
    "pi-extensions/async-exec-bridge/lease.ts": "bun",
    "pi-extensions/async-exec-bridge/notify.ts": "bun",
    "pi-extensions/async-exec-bridge/paths.ts": "bun",
    "pi-extensions/async-exec-bridge/preflight.ts": "bun",
    "pi-extensions/async-exec-bridge/retention.ts": "bun",
    "pi-extensions/async-exec-bridge/spawn.ts": "bun",
    "pi-extensions/async-exec-bridge/state-block.ts": "bun",
    "pi-extensions/async-exec-bridge/telegram.ts": "bun",
    "pi-extensions/async-exec-bridge/timeout.ts": "bun",
}

# The one reason string above, spelled out once.
#
#   bun: the module's real tests are `*.test.ts` run by bun, and this scanner
#        drives `python -m unittest`. `tests/test_async_exec_bridge.py` exists
#        but only asserts structure — package shape, manifest registration,
#        exported handlers — so pointing the sweep at it would report every
#        mutant killed while testing nothing about the logic, which is worse
#        than reporting nothing. Verified 2026-08-12: `bun` is not on PATH on
#        this machine either, so the sweep could not run those tests today even
#        if it knew how.
#
#   TRIGGER for revisiting: teach the runner to invoke `bun test <file>` for
#   modules whose tests are `.test.ts`, on a machine that has bun. 13 modules
#   would come into scope at once.
UNSWEPT_REASONS = {"bun"}

Mutation = namedtuple("Mutation", "offset kind original mutated")


class MutationNotApplied(Exception):
    """The file did not change. Counting that as a kill reports a clean sweep
    over code the runner never touched — `brk.py` grew the same precheck after
    three runs printed OK without having patched anything."""


# --- finding the code ------------------------------------------------------

_SKIP = re.compile(
    r"""(//[^\n]*)            # line comment
      | (/\*.*?\*/)           # block comment
      | ("(?:\\.|[^"\\])*")   # double-quoted
      | ('(?:\\.|[^'\\])*')   # single-quoted
      | (`(?:\\.|[^`\\])*`)   # template literal
      # A regex literal is data, the same as a string. Missing it produced the
      # runner's own first false positive: `blocked-claim.ts:67` is
      # `const TERMINATOR = /[。！？!?\n]|\.(?=\s|$)/g;` and the `!` inside the
      # character class was reported as an untested negation. The lookbehind
      # keeps division out — `/` after a value is a divide, after `= ( , : [ !
      # & | ? { } ; return` it opens a pattern.
      | ((?<=[=(,:\[!&|?{};])\s*/(?![/*])(?:\\.|\[(?:\\.|[^\]\\])*\]|[^/\\\n])+/[gimsuy]*)
    """,
    re.VERBOSE | re.DOTALL,
)


def code_mask(src: str) -> list:
    """True where the character is code rather than prose.

    These files are more comment than code — a refusal message containing
    "blocked && refused" is not a branch, and reporting it as an untested
    mutation trains the reader to skim the survivor list, which is the same as
    not having one.
    """
    mask = [True] * len(src)
    for m in _SKIP.finditer(src):
        for i in range(m.start(), m.end()):
            mask[i] = False
    return mask


# (pattern, replacement, label). Ordered longest-first so `===` is not seen as
# `==` and `!==` is not seen as `!=`.
_OPS = [
    ("!==", "===", "!==->==="),
    ("===", "!==", "===->!=="),
    ("&&", "||", "&&->||"),
    ("||", "&&", "||->&&"),
    ("<=", "<", "<=-><"),
    (">=", ">", ">=->>"),
    ("true", "false", "true->false"),
    ("false", "true", "false->true"),
]

_WORDY = {"true", "false"}
_INT = re.compile(r"\b\d+\b")


def mutations(src: str) -> list:
    """Every single-site mutation available in this source, in file order."""
    mask = code_mask(src)
    found = []
    taken = [False] * len(src)

    for pattern, replacement, label in _OPS:
        start = 0
        while True:
            i = src.find(pattern, start)
            if i < 0:
                break
            start = i + 1
            end = i + len(pattern)
            if not all(mask[i:end]) or any(taken[i:end]):
                continue
            if pattern in _WORDY:
                before = src[i - 1] if i else " "
                after = src[end] if end < len(src) else " "
                if (before.isalnum() or before in "_$") or (after.isalnum() or after in "_$"):
                    continue
            for k in range(i, end):
                taken[k] = True
            found.append(Mutation(i, label, pattern, replacement))

    # Guard clauses are written `if (!x) return ...`, and this operator inverts
    # exactly that shape. It exists because the first sweep could not reach the
    # line Task_003 broke: its surviving break deleted a whole precondition, and
    # nothing in the operator set had a site on that line, so a clean sweep said
    # nothing about it. Operators should be derived from the breaks on record,
    # not chosen because they look standard.
    start = 0
    while True:
        i = src.find("!", start)
        if i < 0:
            break
        start = i + 1
        if not mask[i] or taken[i]:
            continue
        # `!==` is its own operator above; `!=` would become a bare `=`, which
        # is an assignment rather than a comparison — noise, not a survivor.
        if src[i + 1:i + 2] == "=":
            continue
        taken[i] = True
        found.append(Mutation(i, "!x->x", "!", ""))

    for m in _INT.finditer(src):
        i, end = m.start(), m.end()
        if not all(mask[i:end]) or any(taken[i:end]):
            continue
        found.append(Mutation(i, f"{m.group()}->{int(m.group()) + 1}",
                              m.group(), str(int(m.group()) + 1)))

    return sorted(found, key=lambda m: m.offset)


def sample(sites, cap):
    """A deterministic spread across the file, not the first `cap` of them.

    Taking the head would mutate the imports and the top of the module and call
    that a result.
    """
    sites = list(sites)
    if cap is None or len(sites) <= cap or cap <= 0:
        return sites
    step = len(sites) / float(cap)
    return [sites[min(len(sites) - 1, int(i * step))] for i in range(cap)]


# --- applying it, and putting it back --------------------------------------

def apply_mutation(path: str, mutation: Mutation) -> None:
    with open(path, encoding="utf-8", newline="") as f:
        src = f.read()
    at = src[mutation.offset:mutation.offset + len(mutation.original)]
    if at != mutation.original:
        raise MutationNotApplied(
            f"{path}: expected {mutation.original!r} at offset {mutation.offset}, "
            f"found {at!r}")
    new = src[:mutation.offset] + mutation.mutated + src[mutation.offset + len(mutation.original):]
    if new == src:
        raise MutationNotApplied(f"{path}: mutation {mutation.kind} changed nothing")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(new)


# A file that exists only while a source file is mutated on disk.
#
# Measured 2026-08-12: a sweep was killed by a 2-minute command timeout and left
# `readability.ts` holding `index + 2` instead of `index + 1`. The `finally`
# below restores on every exception, but SIGTERM is not an exception — the
# process dies before it runs. The unit tests caught the mutant minutes later,
# which is the system working, but a mutation left in the tree can be committed,
# and `setup.py --mode restore` would install it into ~/.pi and run it in a live
# session.
#
# Signals are handled where they can be (below); this marker covers what they
# cannot, including SIGKILL and a power cut. It cannot restore the bytes — those
# are only in the dead process's memory — so it says which file to check.
MUTATION_MARKER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               ".mutation-in-progress")


# RUN THIS ALONE.
#
# The sweep edits source files in place. Anything else reading the tree at the
# same time — the unit suite, an editor's type checker, `setup.py --mode restore`
# — sees whichever mutant happens to be applied at that instant. Measured
# 2026-08-12: a full `unittest discover` started beside a sweep reported
# `failures=9, errors=13`, all in the module being mutated and none of them real,
# and the sweep's own numbers were untrustworthy for the same reason in reverse.
#
# The marker below makes the damage visible; it cannot make concurrency safe.
def refuse_if_a_mutation_leaked() -> None:
    """Stop if a previous run died with a file mutated."""
    if not os.path.exists(MUTATION_MARKER):
        return
    try:
        with open(MUTATION_MARKER, encoding="utf-8") as f:
            stranded = f.read().strip()
    except OSError:
        stranded = "(unreadable marker)"
    raise SystemExit(
        f"FATAL: a previous sweep died while {stranded} was mutated.\n"
        f"       Check it with `git diff {stranded}` and restore it, then delete\n"
        f"       {MUTATION_MARKER} and run again. Running now would sweep a file\n"
        f"       that is already wrong and report the mutant as killed.")


def install_signal_restore() -> None:
    """Turn the signals that can be caught into exceptions, so `finally` runs.

    SIGINT already raises KeyboardInterrupt. SIGTERM does not, and a command
    timeout sends SIGTERM. SIGKILL cannot be caught by anything — the marker
    above is what covers it.
    """
    def raise_it(signum, _frame):
        raise KeyboardInterrupt(f"signal {signum}")

    for name in ("SIGTERM", "SIGBREAK", "SIGHUP"):
        sig = getattr(signal, name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, raise_it)
        except (ValueError, OSError):
            pass          # not settable on this platform or not the main thread


@contextlib.contextmanager
def mutated_file(path: str, mutation: Mutation):
    """Mutate, yield, and put the original bytes back on every exit path.

    The recipe's escalation trigger names this: a check that can corrupt the
    source it inspects is worse than no check at all. The bytes are held in
    memory and the digest is verified after restoring.
    """
    with open(path, "rb") as f:
        original = f.read()
    digest = hashlib.sha256(original).hexdigest()
    try:
        with open(MUTATION_MARKER, "w", encoding="utf-8") as f:
            f.write(path)
        apply_mutation(path, mutation)
        yield
    finally:
        with open(path, "wb") as f:
            f.write(original)
        with open(path, "rb") as f:
            if hashlib.sha256(f.read()).hexdigest() != digest:
                raise SystemExit(f"FATAL: could not restore {path} — fix it by hand before continuing")
        try:
            os.remove(MUTATION_MARKER)
        except OSError:
            pass


def line_col(src: str, offset: int):
    """Line and column, both 1-based.

    The column is not decoration. `harness-root.ts:40` carries two `||` in one
    condition and both survived the first real run; keyed by line alone they
    collapse into one allowlist entry, so silencing the explainable one would
    silence the other with it.
    """
    line = src.count("\n", 0, offset) + 1
    start = src.rfind("\n", 0, offset) + 1
    return line, offset - start + 1


def _tests_pass(test_modules, cwd) -> bool:
    """True when every mapped test module is green. Stops at the first red,
    which is most of the runtime back on a suite where most mutations die."""
    for t in test_modules:
        if os.path.isabs(t) or t.endswith(".py"):
            cmd = [sys.executable, "-m", "unittest", "discover", "-s",
                   os.path.dirname(t) or ".", "-p", os.path.basename(t)]
        else:
            cmd = [sys.executable, "-m", "unittest", "tests." + t]
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or ROOT)
        if p.returncode != 0:
            return False
    return True


def run_module(module_path, test_modules, cap=DEFAULT_CAP, cwd=None, verbose=True):
    """Mutate one module, returning the survivors as (module, line, kind)."""
    full = module_path if os.path.isabs(module_path) else os.path.join(ROOT, module_path)
    with open(full, encoding="utf-8", newline="") as f:
        src = f.read()

    every = mutations(src)
    picked = sample(every, cap)
    if verbose:
        scope = "all" if len(picked) == len(every) else f"sampled {len(picked)} of {len(every)}"
        print(f"\n{module_path}  ({scope})")

    survivors = []
    for m in picked:
        with mutated_file(full, m):
            killed = not _tests_pass(test_modules, cwd)
        line, col = line_col(src, m.offset)
        if killed:
            if verbose:
                print(f"  killed    line {line:>4}:{col:<3} {m.kind}")
        else:
            survivors.append((module_path, f"{line}:{col}", m.kind))
            if verbose:
                print(f"  SURVIVED  line {line:>4}:{col:<3} {m.kind}")
    return survivors


# --- the verdict -----------------------------------------------------------

def load_allowlist() -> dict:
    if not os.path.isfile(ALLOWLIST):
        return {}
    with open(ALLOWLIST, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def verdict(survivors, allowed) -> int:
    """0 when every survivor is named with an argument, 1 otherwise.

    No percentage. A score target tells you how much untested guard code is
    affordable, and this repo has measured what a threshold does: the citation
    gate took URLs in files from 0 to 10 and fabricated ones from 0 to 4 in the
    same run. A named survivor is a claim someone has to defend; a blank
    allowlist entry is the percentage spelled differently, so it fails too.
    """
    unexplained = []
    moved = []
    for module, where, kind in survivors:
        base = os.path.basename(module)
        key = f"{base}:{where}:{kind}"
        alt = f"{module}:{where}:{kind}"
        reason = allowed.get(key) or allowed.get(alt) or ""
        if not reason.strip():
            # An entry whose site moved. Keys carry line numbers, so inserting a
            # comment above one silently unmatches it and the survivor reappears
            # looking new — that happened three times in one session on
            # 2026-08-10, and the third time was ten minutes after documenting
            # the second. Re-keying by hand treats the symptom; matching on
            # column and operator, which do not move with unrelated edits,
            # treats the cause.
            line, _, col = where.partition(":")
            same = [(k, v) for k, v in allowed.items()
                    if k.startswith(base + ":") and k.endswith(f":{col}:{kind}")
                    and str(v).strip()]
            if len(same) == 1:
                moved.append((same[0][0], key))
                continue
            unexplained.append(key)
    if moved:
        print("")
        print("NOTE: allowlist entries whose line moved. The argument still "
              "stands; only the key is stale:")
        for old_key, new_key in moved:
            print(f"  {old_key}  ->  {new_key}")
    if unexplained:
        print("\nFAIL: mutations survived with no entry in "
              f"{os.path.relpath(ALLOWLIST, ROOT)}:")
        for key in unexplained:
            print(f"  {key}")
        print("\nEach one is a place where changing the guard's behaviour changes "
              "no test. Either add a test that fails, or add an allowlist entry "
              "arguing why no test can tell the difference.")
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser(description="Mutate the guards; require the tests to notice.")
    ap.add_argument("--only", help="substring of a module path")
    ap.add_argument("--cap", type=int, default=DEFAULT_CAP, help="mutations per module")
    ap.add_argument("--all", action="store_true", help="exhaustive (slow)")
    args = ap.parse_args()

    cap = None if args.all else args.cap
    refuse_if_a_mutation_leaked()
    install_signal_restore()

    targets = {k: v for k, v in GUARD_MODULES.items() if not args.only or args.only in k}
    if not targets:
        print(f"no guard module matches {args.only!r}")
        return 2

    survivors = []
    for module, tests in sorted(targets.items()):
        survivors += run_module(module, tests, cap=cap)

    print(f"\n{len(targets)} module(s), {len(survivors)} survivor(s).")
    if not args.all:
        print("Sampled, not exhaustive — a clean sweep here is not a proof of coverage.")
    return verdict(survivors, load_allowlist())


if __name__ == "__main__":
    sys.exit(main())
