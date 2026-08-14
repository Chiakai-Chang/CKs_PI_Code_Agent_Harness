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
    # T-A3 split the restatement in two by source: outside a C.A.S.E. project it
    # quotes the user's request, inside one it quotes the claimed task's Local
    # DoD. One label each, because "a restatement fired" would not say which,
    # and the whole point of the change is which.
    ("task goal restatement", "[C.A.S.E.] 目標重述"),
    ("routing note", "[task-shape] routing note"),
    ("ecc advisory", "[ecc-hooks] advisory"),
    ("compaction kit", "compact-continuation"),
    ("tag transformer", "[SYSTEM CRITICAL AUTO-CORRECTION]"),
]

REFUSALS = [
    ("phase gate", "C.A.S.E. 階段閘"),
    # One label per rule, because "the queue guard fired" hid which rule did.
    # Run 3 of T-A1 was mined as "no queue-guard refusals" when the question was
    # whether the DoD rule specifically had fired — it had not, and it could not.
    #
    # The umbrella entry that split into those rules — ("queue guard",
    # "C.A.S.E. 任務佇列") — is removed rather than kept as a catch-all. Quoting
    # the decision being reversed, per "documented rejections expire": the split
    # was made so that a fired rule could be named, and the umbrella marker
    # matched no string in any bridge, so it could only ever have counted
    # something else. `test_every_marker_exists_in_a_bridge` now fails on that
    # shape instead of leaving it to be noticed by hand.
    ("dod artifacts", "C.A.S.E. 驗收物守衛"),
    ("status value", "C.A.S.E. status guard"),
    ("transition", "C.A.S.E. transition guard"),
    ("one-at-a-time", "C.A.S.E. one-at-a-time guard"),
    ("retrospective", "C.A.S.E. retrospective guard"),
    ("dual-track", "C.A.S.E. dual-track guard"),
    ("boundary", "C.A.S.E. boundary guard"),
    ("tool-first", "tool-first guard"),
    ("containment", "Directory containment"),
    ("harness-root hint", "harness 的安裝位置"),
    ("blocked-claim", "你剛才說"),
    # These four are the guards in research-depth.ts, named by the prefix each
    # one actually prints. The first three were 研究深度 / 引用 / (absent), and
    # measured on 2026-08-14 against `pi-extensions/**/*.ts`:
    #
    #   研究深度  matched no bridge source — dead, could never fire
    #   引用      matched no bridge source — but reported `citation gate 2` on
    #             session 019ffbdd, because 引用 is ordinary Chinese and the
    #             session was written in Chinese. A dead marker is not silent;
    #             it is silent about the guard and loud about everything else.
    #   Artifact guard had no marker at all, so it was invisible in every report
    #             this script has ever produced.
    ("research depth", "Depth guard:"),
    ("artifact gate", "Artifact guard:"),
    ("citation gate", "Citation guard:"),
    # Was 重複 — a word the loop guard does use, and so does everything else. On
    # session 019ffbdd it reported `loop guard 3` while the guard fired 0 times:
    # all three hits were `universal-tag-transformer`'s own parenthetical
    # 「(原文不在此重複,以免你再照著寫一次。)」. The same three messages were
    # already listed correctly under their declared customType, so one batch of
    # messages was counted twice under two different mechanisms.
    #
    # See CUSTOM_TYPE_LABELS below for the structural half of the fix: this
    # marker is now specific, but a wording marker can never be trusted against a
    # message whose sender declared what it is.
    ("loop guard", "發出了完全相同的呼叫"),
    # Three more mechanisms that share the `loop-guard` customType and had no
    # marker, so no report has ever shown them firing.
    ("discarded call", "撞到輸出上限"),
    ("fake-tool strike", "沒有呼叫真正的工具"),
    ("ECC GateGuard", "ECC GateGuard"),
]

# What a customType is allowed to be counted as.
#
# The first version of this said "the sender is authoritative" and labelled a
# custom message by its type alone. That is half true, and the half that is
# false matters: `customType: "loop-guard"` is sent from SEVEN call sites in
# yes-hooks-bridge — the repeat breaker, the blocked-claim guard (both its
# filesystem and its web branch), the output-limit nudge, the transformer's
# three-strike handback, the fake-tool three-strike. The type names the BRIDGE,
# not the mechanism.
#
# So the rule is: the type claims the message (which is what stops one bridge's
# wording being attributed to another's guard — the `loop guard 3` defect on
# session 019ffbdd, where all three hits were the transformer's own
# 「原文不在此重複」), and wording then chooses among the labels that type is
# allowed to carry. A message matching none of them is counted once, in the
# `custom messages` section, under its declared type — not guessed at.
#
# Every customType declared anywhere in `pi-extensions/` must appear here; an
# unlisted one is reported rather than silently dropped.
CUSTOM_TYPE_ALLOWED = {
    "loop-guard": {"loop guard", "blocked-claim", "discarded call",
                   "fake-tool strike"},
    "blocked-claim": {"blocked-claim"},
    "compact-continuation": {"compaction kit"},
    "universal-tag-transformer": {"tag transformer"},
    "case-advance": set(),
    "case-advance-paused": set(),
    "compaction-echo": set(),
    "async-exec": set(),
    "deep-research": set(),
}


def records(path: Path):
    """Message payloads in order. The envelope is `{type:"message", message:{}}`;
    reading the outer object as the message produced three structural zeros in one
    day, so the unwrapping happens once, here.

    `custom_message` records are yielded too, normalised into the same shape with
    role `customMessage`. They are the OTHER delivery channel — `pi.sendMessage`
    — and skipping them made every guard that speaks through it invisible.
    Session `019ffbba` was mined as `injections: none / refusals: none` while
    carrying four of them; `blocked-claim`, the loop guard and the compaction kit
    are sendMessage-only, so those labels could never have counted anything."""
    for line in path.open(encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        kind = rec.get("type")
        if kind == "message":
            msg = rec.get("message")
            if isinstance(msg, dict):
                yield msg
        elif kind == "custom_message":
            content = rec.get("content")
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            elif not isinstance(content, list):
                continue
            yield {"role": "customMessage",
                   "customType": rec.get("customType"),
                   "content": content}


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
        "custom_messages": Counter(), "custom_texts": [],
        "unknown_custom_types": set(),
        "read_paths": [], "write_paths": [],
        "text_after_injection": [],
    }
    injected_seen = False

    def scan(blob: str, msg, allowed=None) -> bool:
        """The declared marker tables, over one delivered message.

        `allowed` restricts which labels may match — see CUSTOM_TYPE_ALLOWED.
        `None` means "no declared sender, every label is a candidate", which is
        the tool_result case."""
        hit = False
        for label, marker in INJECTIONS:
            if allowed is not None and label not in allowed:
                continue
            if marker in blob:
                out["injections"][label] += 1
                hit = True
                if label not in out["injection_texts"]:
                    for b in blocks(msg):
                        t = text_of(b)
                        if marker in t:
                            out["injection_texts"][label] = t
                            break
        for label, marker in REFUSALS:
            if allowed is not None and label not in allowed:
                continue
            if marker in blob:
                # Deliberately does not set `hit`: `hit` drives `injected_seen`,
                # which gates "assistant text after the first INJECTION". A
                # refusal is not an injection, and conflating them would move
                # that excerpt to a different turn.
                out["refusals"][label] += 1
                for b in blocks(msg):
                    t = text_of(b)
                    if marker in t:
                        out["refusal_texts"].append((label, t))
                        break
        return hit

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
            if scan(blob, msg):
                injected_seen = True

        elif role == "customMessage":
            # Counted by the customType the sender declared, not by a marker
            # guessed from the text. The sender is authoritative about which
            # mechanism spoke; the marker tables only say which wording matched,
            # and one bridge's wording HAS been attributed to another's label —
            # `loop guard 3` on session 019ffbdd, from three transformer
            # messages. So the marker tables are not consulted here at all.
            ctype = str(msg.get("customType") or "?")
            out["custom_messages"][ctype] += 1
            first = ""
            for b in blocks(msg):
                t = text_of(b)
                if t:
                    first = t
                    out["custom_texts"].append((ctype, t))
                    break
            injected_seen = True

            allowed = CUSTOM_TYPE_ALLOWED.get(ctype)
            if allowed is None:
                # A bridge shipped a customType nobody taught this script.
                # Reported rather than silently dropped: the last time a
                # delivery channel went unrecognised here, every guard that
                # speaks through it read as "never fired".
                out["unknown_custom_types"].add(ctype)
            elif allowed:
                scan(blob, msg, allowed)
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

    p(f"  custom messages   {sum(d['custom_messages'].values())}"
      "   (pi.sendMessage — the other channel to the model)")
    if d.get("unknown_custom_types"):
        p("  ! customType this script does not know: "
          + ", ".join(sorted(d["unknown_custom_types"]))
          + "  (add it to CUSTOM_TYPE_LABELS)")

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
    p("── sendMessage channel, by declared customType ─────")
    p("  (every sendMessage, grouped by what the sender declared. The two")
    p("   sections above take their label FROM this type, never from wording,")
    p("   so a message here appears there at most once — do not add them up)")
    if not d["custom_messages"]:
        p("  none")
    for label, n in d["custom_messages"].most_common():
        p(f"  {label:<20} {n}")
    ctexts = [t for _, t in d["custom_texts"]]
    cdupes = [i for i in range(1, len(ctexts)) if ctexts[i] == ctexts[i - 1]]
    if cdupes:
        p(f"  ! {len(cdupes)} custom message(s) repeat the one before them, verbatim")
        p("    (a correction repeating itself has taught nothing)")

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
