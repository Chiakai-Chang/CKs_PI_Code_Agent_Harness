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
    "pi-extensions/case-bridge/task-queue-guard.ts": ["test_case_queue_guard", "test_case_guard_bash"],
    "pi-extensions/case-bridge/phase-gate.ts": ["test_phase_tool_gate"],
    "pi-extensions/case-bridge/queue-advancer.ts": ["test_queue_advancer", "test_advancer_settled_loop"],
    "pi-extensions/case-bridge/action-log.ts": ["test_case_action_log"],
    "pi-extensions/case-bridge/approval.ts": ["test_human_approval"],
    "pi-extensions/case-bridge/harness-scope.ts": ["test_harness_scope"],
    "pi-extensions/case-bridge/phase-notice.ts": ["test_phase_opened_notice"],
    "pi-extensions/yes-hooks-bridge/bash-containment.ts": ["test_bash_containment"],
    "pi-extensions/yes-hooks-bridge/blocked-claim.ts": ["test_blocked_claim", "test_blocked_claim_channel", "test_blocked_claim_vocabulary"],
    "pi-extensions/yes-hooks-bridge/research-depth.ts": ["test_research_depth", "test_research_depth_bash"],
    "pi-extensions/yes-hooks-bridge/harness-root.ts": ["test_harness_root_redirect"],
    "pi-extensions/yes-hooks-bridge/loop-detect.ts": ["test_cycle_guard"],
    "pi-extensions/yes-hooks-bridge/compaction-echo.ts": ["test_compaction_echo"],
    "pi-extensions/task-shape-bridge/goal-restate.ts": ["test_goal_restate"],
    "pi-extensions/case-bridge/task-context.ts": ["test_task_context"],
}

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
        apply_mutation(path, mutation)
        yield
    finally:
        with open(path, "wb") as f:
            f.write(original)
        with open(path, "rb") as f:
            if hashlib.sha256(f.read()).hexdigest() != digest:
                raise SystemExit(f"FATAL: could not restore {path} — fix it by hand before continuing")


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
    for module, where, kind in survivors:
        key = f"{os.path.basename(module)}:{where}:{kind}"
        alt = f"{module}:{where}:{kind}"
        reason = allowed.get(key) or allowed.get(alt) or ""
        if not reason.strip():
            unexplained.append(key)
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
