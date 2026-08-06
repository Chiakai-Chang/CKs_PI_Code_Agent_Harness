#!/usr/bin/env python3
"""One reader for Pi session records, instead of a throwaway script each time.

Answering "did the guard fire?" from a session file has been re-derived thirteen
times in a day, and twice the answer was wrong:

  * The depth and artifact gates showed 0 firings and were written up as
    "structurally unverifiable by the probe". They were verifiable — the probe's
    scenario simply never reached the condition.
  * A count of the queue advancer used a glob with an extra directory level and
    returned 0 for a session containing 4, one step from declaring a working
    mechanism dead.

Both failures print the same character: 0. So this reports the files it scanned
before it reports anything found in them. A zero from an empty match set and a
zero from a real absence are answers to different questions and must never look
alike.

Usage:
    python scripts/session-report.py <session.jsonl | directory>
    python scripts/session-report.py ~/.pi/agent/sessions --guards-only
    python scripts/session-report.py --unharvested          # queue vs docs
"""

import argparse
import collections
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Refusal text that reaches the model as a tool result. Kept in step with
# scripts/measure-triggers.py — two lists of the same guards drift, and this
# repo has the scar where uninstall.py managed 5 bridges to restore.py's 11.
GUARD_MARKERS = (
    "Depth guard",
    "Artifact guard",
    "Citation guard",
    "Repeat-lookup guard",
    "[task-shape]",
    "C.A.S.E. transition guard",
    "C.A.S.E. one-at-a-time guard",
    "C.A.S.E. retrospective guard",
    "C.A.S.E. dual-track guard",
    "C.A.S.E. boundary guard",
    "Directory containment",
)

URL_RE = re.compile(r"https?://[^\s<>\)\]\"'，。、]+")


def session_files(target):
    """Every .jsonl under a path, at any depth.

    Depth is the point. The count that nearly killed a working mechanism came
    from a glob that assumed one directory level and found none.
    """
    if os.path.isfile(target):
        return [target]
    found = []
    for dirpath, _dirs, files in os.walk(target):
        for name in sorted(files):
            if name.endswith(".jsonl"):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def _text_of(content):
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return " ".join(b.get("text", "") for b in content if isinstance(b, dict))


def report(target):
    """What a set of sessions actually did."""
    files = session_files(target) if os.path.exists(target) else []
    warnings = []
    if not os.path.exists(target):
        warnings.append("path does not exist: %s" % target)
    elif not files:
        warnings.append("scanned %s and found no .jsonl session files" % target)

    tools = collections.Counter()
    guards = collections.Counter()
    custom = collections.Counter()
    skills = []
    opened = []
    written = []
    # Injections arriving between two assistant turns. Task_001 flagged that
    # nothing coordinates corrections across bridges, and Task_002 answered
    # "not observed this time" — which is not evidence. A number accumulates.
    max_injections = 0
    run = 0

    for path in files:
        try:
            fh = io.open(path, encoding="utf-8", errors="replace")
        except OSError:
            warnings.append("could not read %s" % path)
            continue
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue

                if entry.get("type") == "custom_message":
                    custom[entry.get("customType") or "?"] += 1
                    run += 1
                    max_injections = max(max_injections, run)
                    continue

                msg = entry.get("message") or {}
                role = msg.get("role")

                if role == "toolResult":
                    text = _text_of(msg.get("content"))
                    for marker in GUARD_MARKERS:
                        if marker in text:
                            guards[marker] += 1
                    continue

                if role != "assistant":
                    continue
                run = 0
                for block in msg.get("content") or []:
                    if not isinstance(block, dict) or block.get("type") != "toolCall":
                        continue
                    name = block.get("name")
                    tools[name] += 1
                    args = block.get("arguments") or {}
                    path_arg = str(args.get("path") or "")
                    if path_arg.upper().endswith("SKILL.MD"):
                        parts = path_arg.replace("\\", "/").split("/")
                        if len(parts) > 1 and parts[-2] not in skills:
                            skills.append(parts[-2])
                    if name == "web_open" and isinstance(args.get("url"), str):
                        opened.append(args["url"])
                    if name in ("write", "edit"):
                        if isinstance(args.get("content"), str):
                            written.append(args["content"])
                        for e in args.get("edits") or []:
                            if isinstance(e, dict) and isinstance(e.get("newText"), str):
                                written.append(e["newText"])

    body = "\n".join(written)
    found_urls = {u.rstrip(".,;") for u in URL_RE.findall(body)}
    open_set = {u.rstrip(".,;") for u in opened}
    traceable = {u for u in found_urls
                 if any(u.startswith(p[:40]) or p.startswith(u[:40]) for p in open_set)}

    return {
        "files": files,
        "warnings": warnings,
        "tools": dict(tools),
        "guards": {k: v for k, v in guards.items() if v},
        "custom": dict(custom),
        "skills": skills,
        "urls_in_files": len(found_urls),
        "urls_opened": len(traceable),
        "max_injections_per_turn": max_injections,
    }


def unharvested(queue_dir, docs_dir):
    """Task packages whose output nothing in docs/ mentions.

    02_Task_Queue/ is gitignored — the protocol calls it agent workspace — so a
    conclusion left there is one `git clean` from gone. Task_002's survived only
    because `git commit` reported "nothing to commit" and somebody noticed.

    This lists; it does not move. What is worth keeping differs per task, and
    copying everything would bury docs/ in intermediate state.
    """
    if not os.path.isdir(queue_dir):
        return []
    mentioned = ""
    for dirpath, _dirs, files in os.walk(docs_dir):
        for name in files:
            if name.endswith((".md", ".jsonl")):
                try:
                    with io.open(os.path.join(dirpath, name), encoding="utf-8",
                                 errors="replace") as fh:
                        mentioned += fh.read()
                except OSError:
                    pass
    out = []
    for name in sorted(os.listdir(queue_dir)):
        task = os.path.join(queue_dir, name)
        if not os.path.isdir(task) or not os.path.isfile(os.path.join(task, "output.md")):
            continue
        if name not in mentioned:
            out.append(name)
    return out


def harvest_status(queue_dir, docs_dir):
    """Every task with an output.md, and whether docs/ mentions it at all.

    A mention is not preservation, and the first real run of this check proved
    it: one task's name appeared in docs/ only inside a quoted session
    transcript and one sentence about a guard, while its retro's three pieces of
    upstream feedback existed nowhere outside the gitignored queue. Reporting
    "all clear" there was worse than reporting nothing.

    So this lists them all and leaves the judgement to a human — which is what
    the panel decided anyway: list, do not move.
    """
    if not os.path.isdir(queue_dir):
        return []
    missing = set(unharvested(queue_dir, docs_dir))
    out = []
    for name in sorted(os.listdir(queue_dir)):
        task = os.path.join(queue_dir, name)
        if os.path.isdir(task) and os.path.isfile(os.path.join(task, "output.md")):
            out.append((name, name not in missing))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="session-report.py", description=__doc__)
    ap.add_argument("target", nargs="?", help="a session .jsonl or a directory of them")
    ap.add_argument("--guards-only", action="store_true")
    ap.add_argument("--unharvested", action="store_true",
                    help="list task packages whose output nothing in docs/ mentions")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.unharvested:
        rows = harvest_status(os.path.join(ROOT, "02_Task_Queue"), os.path.join(ROOT, "docs"))
        if not rows:
            print("no task package has an output.md yet")
            return 0
        print("task packages with an output.md — the queue is gitignored, so these are "
              "one `git clean` from gone:")
        for name, mentioned in rows:
            print("  %-42s %s" % (name, "named in docs/" if mentioned else "NOT NAMED in docs/"))
        print("\nA name appearing in docs/ is not the same as its conclusions being preserved.")
        print("The first run of this check said 'all clear' while a retro's three pieces of")
        print("upstream feedback existed nowhere outside the queue — the only mention of that")
        print("task was inside a quoted session transcript.")
        return 0

    if not args.target:
        ap.print_usage(sys.stderr)
        return 1

    rep = report(args.target)
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0

    # Files first, always. This is the whole point.
    print("scanned %d session file(s) under %s" % (len(rep["files"]), args.target))
    for path in rep["files"][:10]:
        print("   %s" % os.path.basename(path))
    if len(rep["files"]) > 10:
        print("   … and %d more" % (len(rep["files"]) - 10))
    for w in rep["warnings"]:
        print("   ! %s" % w)
    print()

    if rep["guards"]:
        print("guards fired:")
        for name, n in sorted(rep["guards"].items()):
            print("   %-32s %d" % (name, n))
    else:
        print("guards fired: none  (with %d file(s) scanned)" % len(rep["files"]))
    if args.guards_only:
        return 0
    print()

    if rep["tools"]:
        print("tools: %s" % ", ".join("%s %d" % (k, v) for k, v in sorted(rep["tools"].items())))
    print("urls in written files: %d (of which opened: %d)"
          % (rep["urls_in_files"], rep["urls_opened"]))
    if rep["skills"]:
        print("skills read: %s" % ", ".join(rep["skills"]))
    if rep["custom"]:
        print("harness messages: %s"
              % ", ".join("%s %d" % (k, v) for k, v in sorted(rep["custom"].items())))
        print("most injections between two turns: %d" % rep["max_injections_per_turn"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
