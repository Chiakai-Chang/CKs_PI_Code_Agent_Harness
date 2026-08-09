#!/usr/bin/env python3
"""What the classifier thought, across real sessions.

Usage:
    python scripts/report-task-shapes.py                 # recorded entries
    python scripts/report-task-shapes.py --from-prompts  # classify history directly

Records that nobody reads are the failure this repo keeps meeting - an unread
`global_dod.md` sat as an unfilled template for weeks. So the classifier ships
with the thing that reads it back.

Two modes on purpose. `--from-prompts` re-classifies the first user prompt of
every past session, which works today and needs no recorded entries; the
default reads what the bridge actually wrote, which is the only way to find out
whether `appendEntry` reaches the transcript at all. The type says it persists
session state; a type has never told this project when or whether an event
fires, and the difference has cost a day before.

Measurement fixtures are excluded by directory: they are prompts I wrote, not
work the owner asked for, and averaging them in would be measuring myself.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SESSIONS = Path(os.path.expanduser("~")) / ".pi" / "agent" / "sessions"
MOD = ROOT / "pi-extensions" / "task-shape-bridge" / "shape.ts"
FIXTURE_MARKERS = ("scratchpad", "AppData-Local-Temp", "advancer-")


def real_session_files():
    if not SESSIONS.is_dir():
        return []
    return [p for p in SESSIONS.glob("*/*.jsonl")
            if not any(m in p.parent.name for m in FIXTURE_MARKERS)]


def first_user_prompt(path: Path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                rec = json.loads(line.strip() or "{}")
                if rec.get("type") != "message":
                    continue
                msg = rec.get("message") or {}
                if msg.get("role") != "user":
                    continue
                content = msg.get("content")
                if isinstance(content, str):
                    return content
                return " ".join(b.get("text", "") for b in content or []
                                if isinstance(b, dict))
    except Exception:
        return None
    return None


def recorded_shapes(path: Path):
    """Entries the bridge wrote, if `appendEntry` reaches the transcript."""
    out = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                rec = json.loads(line.strip() or "{}")
                if rec.get("customType") == "case.task-shape":
                    out.append(rec.get("data") or rec.get("content") or {})
    except Exception:
        pass
    return out


def classify_many(prompts):
    driver = Path(tempfile.mkdtemp()) / "shape.mjs"
    url = "file:///" + str(MOD).replace("\\", "/")
    driver.write_text(
        "import {classifyRequest} from %s;\nconst P=%s;\n"
        "process.stdout.write(JSON.stringify(P.map(p=>classifyRequest(p))));"
        % (json.dumps(url), json.dumps(prompts)), encoding="utf-8")
    p = subprocess.run(["node", str(driver)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=180)
    if p.returncode != 0:
        raise SystemExit("node failed:\n" + p.stderr)
    return json.loads(p.stdout)


def main() -> int:
    ap = argparse.ArgumentParser(description="Report task-shape classifications.")
    ap.add_argument("--from-prompts", action="store_true",
                    help="re-classify session history instead of reading recorded entries")
    ap.add_argument("--show", choices=["phased", "all"], default="phased",
                    help="phased = list the multi-step prompts")
    args = ap.parse_args()

    files = real_session_files()
    if not files:
        print(f"no sessions under {SESSIONS}")
        return 0

    if args.from_prompts:
        pairs = [(f, first_user_prompt(f)) for f in files]
        pairs = [(f, t) for f, t in pairs if t and t.strip()]
        shapes = classify_many([t for _, t in pairs])
        rows = list(zip((t for _, t in pairs), shapes))
        source = "re-classified from session history"
    else:
        rows = []
        for f in files:
            for entry in recorded_shapes(f):
                rows.append((entry.get("prompt", ""), entry))
        source = "recorded by the bridge"
        if not rows:
            print("No `case.task-shape` entries found in any session.")
            print("Either no session has run since the classifier landed, or")
            print("`appendEntry` does not reach the transcript — which is worth")
            print("knowing either way. Try --from-prompts meanwhile.")
            return 0

    counts = collections.Counter("multi-step" if s.get("multiStep") else "single-step"
                                 for _, s in rows)
    total = len(rows)
    print(f"{total} prompts ({source}), fixtures excluded")
    for name in ("single-step", "multi-step"):
        n = counts.get(name, 0)
        print(f"  {name:<12} {n:>4}   {100.0 * n / total:5.1f}%")

    distinct = {t for t, s in rows if s.get("multiStep")}
    print("")
    print(f"multi-step prompts: {counts.get('multi-step', 0)} occurrences, "
          f"{len(distinct)} distinct")
    if args.show == "phased":   # the multi-step ones
        for t in sorted(distinct):
            print(f"  [{len(t):>6}] {t.strip()[:90]}")
    print("\nNothing is gated on this. The threshold gets chosen when these "
          "numbers have been argued with.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
