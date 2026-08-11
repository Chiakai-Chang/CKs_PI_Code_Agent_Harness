#!/usr/bin/env python3
"""Did the run plan before it searched? Counted over real session history.

    python scripts/report-plan-order.py
    python scripts/report-plan-order.py --all        # include my own probe runs
    python scripts/report-plan-order.py --verbose    # one line per session

T-A8 exists because run 10 (2026-08-12) delivered the routing note and the model
still issued two `web_search` calls before it wrote `task_plan.md`. The obvious
next move is a gate at `tool_call` — and this repo has measured what gates do:
the citation gate took URLs-in-files from 0 to 10 and fabricated ones from 0 to 4
in the same run. A threshold defines the shape of the evasion.

So: measure first. This reports how often the order is actually wrong, across
the sessions that already exist, before anything is built.

WHAT COUNTS, declared before the counting:

* eligible session = at least one `web_search` call. A session that never
  searched cannot search-before-planning, and including it would dilute the rate
  with runs the question does not apply to.
* plan write = a `write`/`edit` whose file is `task_plan.md`, `planning.md` or
  `plan.md` (any directory, including `.planning/<id>/`). `findings.md` is a
  research artifact, not a plan, and is not counted.
* verdict per session:
    plan-first    a plan write occurs BEFORE the first web_search
    search-first  a plan write occurs, but after
    no-plan       searches happened and no plan was ever written

EXCLUDED BY DEFAULT, and why:

* `…AppData-Local-Temp…` — my own probe scratchpads. Their working directories
  carry the harness name, which is the confound that invalidated four earlier
  probe runs.
* `PiTaskLab` — my C.A.S.E. fixture. Planning there is `planning.md` inside a
  task package under a phase gate that refuses deliverables without it, so its
  order is enforced by a different mechanism and pooling it would flatter this
  number.
* `TruthProbeVerify` — my replica of the owner's project, run by me, not by the
  owner. Reported separately rather than pooled.

Pooling runs whose configuration differs is the mistake `measure-advancer.py`
refuses to make; this is the same rule applied to provenance.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

SESSIONS = Path(os.path.expanduser("~")) / ".pi" / "agent" / "sessions"

MINE = ("appdata-local-temp", "pitasklab", "truthprobeverify")
PLAN_FILES = ("task_plan.md", "planning.md", "plan.md")
SEARCH_TOOLS = ("web_search", "deep_research")
WRITE_TOOLS = ("write", "edit")


def calls(path: Path):
    """(toolName, argument-blob) for every tool call, in order."""
    try:
        lines = path.open(encoding="utf-8", errors="replace").readlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        msg = rec.get("message") if isinstance(rec.get("message"), dict) else rec
        if msg.get("role") != "assistant":
            continue
        for block in msg.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "toolCall":
                args = block.get("arguments") or {}
                yield str(block.get("name") or ""), args


def verdict(path: Path):
    """(verdict, first_search_index, first_plan_index, n_calls) or None."""
    first_search = None
    first_plan = None
    n = 0
    for name, args in calls(path):
        n += 1
        low = name.lower()
        if low in SEARCH_TOOLS and first_search is None:
            first_search = n
        if low in WRITE_TOOLS and first_plan is None:
            target = str(args.get("path") or "").replace("\\", "/").lower()
            if target.rsplit("/", 1)[-1] in PLAN_FILES:
                first_plan = n
    if first_search is None:
        return None                      # not an eligible session
    if first_plan is None:
        return ("no-plan", first_search, None, n)
    return ("plan-first" if first_plan < first_search else "search-first",
            first_search, first_plan, n)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="include my probe scratchpads and fixtures")
    ap.add_argument("--verbose", action="store_true", help="one line per session")
    args = ap.parse_args()

    if not SESSIONS.is_dir():
        print("no session directory at %s" % SESSIONS)
        return 1

    tally: Counter[str] = Counter()
    per_workspace: dict[str, Counter[str]] = {}
    rows = []
    skipped = 0

    for workspace in sorted(SESSIONS.iterdir()):
        if not workspace.is_dir():
            continue
        mine = any(m in workspace.name.lower() for m in MINE)
        if mine and not args.all:
            skipped += len(list(workspace.glob("*.jsonl")))
            continue
        for session in sorted(workspace.glob("*.jsonl")):
            got = verdict(session)
            if got is None:
                continue
            kind, s_at, p_at, n = got
            tally[kind] += 1
            per_workspace.setdefault(workspace.name, Counter())[kind] += 1
            rows.append((workspace.name, session.name, kind, s_at, p_at, n))

    total = sum(tally.values())
    print("sessions that searched at least once: %d" % total)
    if not args.all:
        print("(excluded %d sessions in my own probe scratchpads and fixtures — "
              "see this file's header)" % skipped)
    print()
    for kind in ("plan-first", "search-first", "no-plan"):
        c = tally[kind]
        pct = (100.0 * c / total) if total else 0.0
        print("  %-12s %3d   %5.1f%%" % (kind, c, pct))
    print()
    # A session with three tool calls that never wrote a plan is not the
    # complaint; a thirty-call one is. The rate without this split reads as an
    # indictment of runs that were right to skip planning.
    buckets = [("1-4 calls", 1, 4), ("5-9", 5, 9), ("10-19", 10, 19), ("20+", 20, 10 ** 9)]
    print("no-plan sessions by size (tool calls):")
    for label, lo, hi in buckets:
        n_np = sum(1 for r in rows if r[2] == "no-plan" and lo <= r[5] <= hi)
        n_all = sum(1 for r in rows if lo <= r[5] <= hi)
        print("  %-10s %3d of %3d" % (label, n_np, n_all))
    print()
    print("by workspace:")
    for name, counts in sorted(per_workspace.items()):
        print("  %-42s %s" % (name.strip("-"),
                              ", ".join("%s %d" % (k, v) for k, v in sorted(counts.items()))))
    if args.verbose:
        print()
        print("  %-30s %-12s %-6s %-6s %s" % ("session", "verdict", "search", "plan", "calls"))
        for ws, sess, kind, s_at, p_at, n in rows:
            print("  %-30s %-12s %-6s %-6s %d"
                  % (sess[:30], kind, s_at, p_at if p_at else "-", n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
