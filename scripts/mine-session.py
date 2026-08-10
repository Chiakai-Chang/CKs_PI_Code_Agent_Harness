#!/usr/bin/env python3
"""Read one session the way the last four were read by hand.

Every substantive finding on 2026-08-09/10 came from opening a session log and
looking, not from an A/B: `2>/dev/null` extracted as a write target, a refusal
promising 下一次我不會再擋 and then blocking seven more times, five byte-identical
repeats, one guard's diagnosis drowned under another's nine, an injection whose
number disagreed with what the model could see. The A/B path spent seven runs and
produced no conclusion.

The difference matters because **controlling variables is only needed to measure
an effect, not to find a defect**. `cp a b 2>/dev/null` losing its destination is
a defect whatever else changed in the same batch. So the cheaper loop is: change
several things, run one realistic session, and read its log properly.

Reading it properly meant re-deriving the same queries four times. This is that
checklist, fixed:

    counts        turns, tool calls, batching, errors
    sequence      what it actually did, in order
    injections    which bridge text reached the model, how often, where
    refusals      which guard spoke, how many times, and whether it repeated
    attribution   did the model already read what was injected to it
    outcome       what changed on disk

    python scripts/mine-session.py <session.jsonl|workspace-substring>
    python scripts/mine-session.py --latest
    python scripts/mine-session.py --latest --full     # verbatim injected blocks

It reports and never judges. A number here is an observation; whether it is good
is a question for the person reading.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

SESSIONS = Path(os.path.expanduser("~")) / ".pi" / "agent" / "sessions"

# Declared, never derived. Deriving these by scanning the bridges for string
# literals was the first design and it found the labels inside comments and test
# fixtures too. A label that stops matching should fail loudly by reporting zero,
# which is a finding, rather than silently matching something else.
INJECTIONS = [
    ("task constitution", "[C.A.S.E.] 任務專屬憲法"),
    ("phase reopened", "階段閘已經放開"),
    ("goal restatement", "[task-shape] 目標重述"),
    ("routing note", "[task-shape] routing note"),
    ("ecc advisory", "[ecc-hooks] advisory"),
    ("compaction kit", "compact-continuation"),
]

REFUSALS = [
    ("phase gate", "C.A.S.E. 階段閘"),
    ("queue guard", "C.A.S.E. 任務佇列"),
    ("tool-first", "tool-first guard"),
    ("containment", "Directory containment"),
    ("harness-root hint", "harness 的安裝位置"),
    ("blocked-claim", "你剛才說"),
    ("research depth", "研究深度"),
    ("citation gate", "引用"),
    ("loop guard", "重複"),
    ("ECC GateGuard", "ECC GateGuard"),
]


def records(path: Path):
    """Message payloads in order. The envelope is `{type:"message", message:{}}`;
    reading the outer object as the message produced three structural zeros in one
    day, so the unwrapping happens once, here."""
    for line in path.open(encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if rec.get("type") != "message":
            continue
        msg = rec.get("message")
        if isinstance(msg, dict):
            yield msg


def text_of(block) -> str:
    return block.get("text", "") if isinstance(block, dict) else ""


def blocks(msg):
    c = msg.get("content")
    return c if isinstance(c, list) else []


def find_session(arg: str | None, latest: bool) -> Path | None:
    if arg and Path(arg).is_file():
        return Path(arg)
    if not SESSIONS.is_dir():
        return None
    files = list(SESSIONS.glob("*/*.jsonl"))
    if arg:
        files = [f for f in files
                 if arg.lower() in f.parent.name.lower() or arg.lower() in f.name.lower()]
    if not files:
        return None
    if latest or arg:
        return max(files, key=lambda f: f.stat().st_mtime)
    return None


def mine(path: Path) -> dict:
    out = {
        "session": path.name,
        "workspace": path.parent.name,
        "users": 0, "assistants": 0, "tool_calls": 0,
        "errors": 0, "batches": [], "sequence": [],
        "injections": Counter(), "injection_texts": {},
        "refusals": Counter(), "refusal_texts": [],
        "read_paths": [], "write_paths": [],
        "text_after_injection": [],
    }
    injected_seen = False
    for msg in records(path):
        role = msg.get("role")
        blob = json.dumps(msg, ensure_ascii=False)

        if role == "user":
            out["users"] += 1
        elif role == "assistant":
            out["assistants"] += 1
            n = 0
            for b in blocks(msg):
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "toolCall":
                    n += 1
                    out["tool_calls"] += 1
                    args = b.get("arguments") or {}
                    detail = str(args.get("command") or args.get("path")
                                 or args.get("query") or args.get("pattern") or "")
                    name = str(b.get("name") or "?")
                    out["sequence"].append((name, detail))
                    if name in ("read", "grep", "find", "ls"):
                        out["read_paths"].append(detail)
                    elif name in ("write", "edit"):
                        out["write_paths"].append(detail)
                elif b.get("type") == "text" and injected_seen:
                    t = b.get("text", "").strip()
                    if t and len(out["text_after_injection"]) < 3:
                        out["text_after_injection"].append(t[:400])
            if n:
                out["batches"].append(n)

        elif role == "toolResult":
            if msg.get("isError") is True:
                out["errors"] += 1
            for label, marker in INJECTIONS:
                if marker in blob:
                    out["injections"][label] += 1
                    injected_seen = True
                    if label not in out["injection_texts"]:
                        for b in blocks(msg):
                            t = text_of(b)
                            if marker in t:
                                out["injection_texts"][label] = t
                                break
            for label, marker in REFUSALS:
                if marker in blob:
                    out["refusals"][label] += 1
                    for b in blocks(msg):
                        t = text_of(b)
                        if marker in t:
                            out["refusal_texts"].append((label, t))
                            break
    return out


def report(d: dict, full: bool, w) -> None:
    p = lambda *a: print(*a, file=w)
    p(f"session   {d['session']}")
    p(f"workspace {d['workspace']}")
    p("")
    p("── counts ─────────────────────────────────────────")
    p(f"  user messages     {d['users']}")
    p(f"  assistant turns   {d['assistants']}")
    p(f"  tool calls        {d['tool_calls']}")
    p(f"  errored results   {d['errors']}")
    if d["batches"]:
        p(f"  calls per turn    {'/'.join(str(b) for b in d['batches'])}")
        p("                    (an extension counting tool_result lags this — "
          "see CLAUDE.md)")
    if d["users"] and d["assistants"]:
        p(f"  turns per prompt  {d['assistants'] / d['users']:.1f}"
          "   (before_agent_start fires once per PROMPT)")

    p("")
    p("── injections that reached the model ───────────────")
    if not d["injections"]:
        p("  none. Either nothing was armed, or nothing was delivered —")
        p("  a green unit test does not distinguish these two.")
    for label, n in d["injections"].most_common():
        p(f"  {label:<20} {n}")

    p("")
    p("── refusals ───────────────────────────────────────")
    if not d["refusals"]:
        p("  none")
    for label, n in d["refusals"].most_common():
        p(f"  {label:<20} {n}")
    texts = [t for _, t in d["refusal_texts"]]
    dupes = [i for i in range(1, len(texts)) if texts[i] == texts[i - 1]]
    if dupes:
        p(f"  ! {len(dupes)} refusal(s) repeat the one before them, verbatim")
        p("    (a guard repeating itself has taught nothing)")
    if len(texts) > 1 and len(set(texts)) == 1:
        p("  ! every refusal was the same text")

    p("")
    p("── attribution risk ───────────────────────────────")
    reads = " ".join(d["read_paths"]).lower()
    risky = [f for f in ("role.md", "recipe.md", "planning.md", "constitution")
             if f in reads]
    if risky:
        p(f"  the model READ {', '.join(risky)} itself.")
        p("  Anything injected from those files cannot be credited to the")
        p("  injection in this run.")
    else:
        p("  no injected source was read by the model directly")

    p("")
    p("── sequence ───────────────────────────────────────")
    for i, (name, detail) in enumerate(d["sequence"], 1):
        p(f"  {i:>3} {name:<6} {detail[:78]}")

    if d["text_after_injection"]:
        p("")
        p("── assistant text after the first injection ────────")
        for t in d["text_after_injection"]:
            p("  " + t.replace("\n", "\n  "))

    if full and d["injection_texts"]:
        p("")
        p("── injected blocks, verbatim ───────────────────────")
        for label, t in d["injection_texts"].items():
            p(f"\n  [{label}]")
            p("  " + t.replace("\n", "\n  "))


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("session", nargs="?",
                    help="a .jsonl path, or a substring of the workspace name")
    ap.add_argument("--latest", action="store_true", help="the newest session")
    ap.add_argument("--full", action="store_true",
                    help="also print each injected block verbatim")
    ap.add_argument("--out", help="write the report here (UTF-8) instead of stdout")
    args = ap.parse_args()

    path = find_session(args.session, args.latest)
    if not path:
        print("no session found. Pass a path, a workspace substring, or --latest.")
        return 1

    d = mine(path)
    # UTF-8 explicitly: this console is cp950 and every report here is Chinese.
    # Mojibake in a report is how a real finding gets skimmed past.
    if args.out:
        with io.open(args.out, "w", encoding="utf-8") as f:
            report(d, args.full, f)
        print(f"wrote {args.out}")
    else:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        report(d, args.full, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
