#!/usr/bin/env python3
"""Measure whether the harness's mechanisms actually fire, without naming them.

Every prompt-shaping decision in this harness — the skill catalog wording, the
scoped web_search guidance, the tiered core list, the reading view — has been
tuned blind and validated by a single manual run. That is how five measurement
mistakes got made in one day, each stated confidently before being corrected.

This converts "we hope it triggers" into a number that can be re-run after any
prompt change.

DESIGN NOTES (each of these came from reviewing the first draft of this script)

  * REPEATS. The local model runs at temperature 0.6; a single run says almost
    nothing. Every scenario runs N times (default 3) and reports a rate.
  * ISOLATED SESSIONS. Runs write to a temp --session-dir. Without this the
    harness's own measurements get polluted by its test runs — exactly what
    happened when `agent-architecture-audit` showed 4 loads in the real history
    and all 4 were test runs.
  * NEUTRAL CWD. Scenarios run in an empty temp directory, so the model does not
    see this repo's active plan, CASE state or files. Those are noise for a
    question about general triggering.
  * NEGATIVE SCENARIOS. Some scenarios assert a mechanism must NOT fire.
    Measuring only "did it trigger" rewards ever more forceful guidance, which
    is precisely how web_search's "for any task" wording came to swallow every
    other tool.
  * NO BASELINE FOR PAST CHANGES. Today's wording changes were made before this
    existed, so this cannot retroactively prove they helped. It establishes the
    baseline from here on. Do not read the first run as a verdict on them.

Usage:
  python scripts/measure-triggers.py                # all scenarios, 3 runs each
  python scripts/measure-triggers.py --repeats 1    # quick smoke
  python scripts/measure-triggers.py --only web-read,deep-research
  python scripts/measure-triggers.py --timeout 900
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

# Each scenario states a task the way a user would, WITHOUT naming the tool or
# skill. `expect` is what should happen; `forbid` is what must not.
SCENARIOS = [
    {
        "id": "web-read",
        "prompt": "What does https://en.wikipedia.org/wiki/Accessibility_tree say? Summarize it in two sentences.",
        "expect_tools": ["web_open", "web_search"],
        "expect_result": {"no_element_refs": True},
        "why": "reading a URL should go through the stealth browser and come back as a reading view",
    },
    {
        "id": "deep-research",
        "prompt": ("Compare the licensing terms, the pricing model, and the self-hosting story "
                   "of Grafana versus Kibana. I want all three covered."),
        "expect_tools": ["deep_research"],
        "why": "three separate lookups is what deep_research exists for; web_search would put every page in context",
    },
    {
        "id": "single-lookup-stays-cheap",
        "prompt": "What is the latest released version of the Zig programming language?",
        "expect_tools": ["web_search", "web_open"],
        "forbid_tools": ["deep_research"],
        "why": "NEGATIVE: one lookup must not pay for a subagent run",
    },
    {
        "id": "local-not-web",
        "prompt": "Is there a skill available here for auditing an agent architecture? If so, load it.",
        "expect_tools": ["read"],
        "forbid_tools": ["web_search"],
        "why": "NEGATIVE: a local skill must not be looked up on the web",
    },
    {
        "id": "debug-methodology",
        "prompt": ("A test in my project passes alone but fails when the suite runs. "
                   "I have tried rerunning it. What should I do?"),
        "expect_skill_read": ["systematic-debugging", "diagnosing-bugs", "investigation-first"],
        "why": "the harness routes debugging to a methodology skill; if none loads, the routing is decorative",
    },
]


def pi_executable():
    """Resolve pi to a real path.

    On Windows npm installs it as pi.CMD; passing the bare name to
    subprocess.run without a shell raises WinError 2 even though it is on PATH.
    """
    return shutil.which("pi")


PI = None


def run_once(scenario, cwd, session_dir, timeout):
    """Run one scenario; return (tools_called, skills_read, results_text, error)."""
    cmd = [PI, "--print", "--mode", "json", "--session-dir", session_dir, scenario["prompt"]]
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return [], [], "", "timeout after %ss" % timeout
    tools, skills, results = [], [], []
    for line in p.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        msg = ev.get("message") or {}
        if msg.get("role") == "assistant":
            for c in msg.get("content", []) or []:
                if c.get("type") == "toolCall":
                    tools.append(c.get("name"))
                    if c.get("name") == "read":
                        path = str((c.get("arguments") or {}).get("path") or "")
                        if path.upper().endswith("SKILL.MD"):
                            parts = path.replace("\\", "/").split("/")
                            if len(parts) > 1:
                                skills.append(parts[-2])
        if msg.get("role") == "toolResult":
            content = msg.get("content")
            text = content if isinstance(content, str) else " ".join(
                x.get("text", "") for x in (content or []) if isinstance(x, dict))
            results.append(text)
    err = "" if p.returncode == 0 else "exit %s: %s" % (p.returncode, p.stderr[-200:])
    return tools, skills, "\n".join(results), err


def judge(scenario, tools, skills, results):
    """Return (passed, note). Objective checks only — no model grading."""
    notes = []
    ok = True

    want = scenario.get("expect_tools")
    if want:
        if not any(t in tools for t in want):
            ok = False
            notes.append("none of %s called (called: %s)" % ("/".join(want), ", ".join(tools) or "nothing"))

    forbid = scenario.get("forbid_tools", [])
    hit = [t for t in forbid if t in tools]
    if hit:
        ok = False
        notes.append("called forbidden %s" % ", ".join(hit))

    want_skill = scenario.get("expect_skill_read")
    if want_skill:
        if not any(s in skills for s in want_skill):
            ok = False
            notes.append("no methodology skill loaded (read: %s)" % (", ".join(skills) or "none"))

    checks = scenario.get("expect_result") or {}
    if checks.get("no_element_refs") and results:
        # `results` is one joined string. An earlier version iterated it as if it
        # were a list of results, which walks it character by character — the
        # check silently never fired. Isolate the page-result blocks by their
        # header instead, so a stray "[e1]" in unrelated output cannot fail a run.
        blocks = results.split("[tab ")
        page_blocks = [b for b in blocks[1:] if "now the current page" in b]
        if any(re.search(r"\[e\d+\]", b) for b in page_blocks):
            ok = False
            notes.append("page result still carried [eN] refs")

    return ok, "; ".join(notes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--only", default="")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--keep-sessions", action="store_true")
    ap.add_argument("--report", default=None,
                    help="append the run to a JSONL baseline file for later comparison")
    args = ap.parse_args()

    global PI
    PI = pi_executable()
    if not PI:
        print("pi is not on PATH — cannot measure triggering. Not reporting zeros for a run "
              "that never happened.", file=sys.stderr)
        return 2

    wanted = {s.strip() for s in args.only.split(",") if s.strip()}
    scenarios = [s for s in SCENARIOS if not wanted or s["id"] in wanted]
    if not scenarios:
        print("no scenarios matched --only", file=sys.stderr)
        return 2

    session_dir = tempfile.mkdtemp(prefix="pi-trigger-sessions-")
    work_dir = tempfile.mkdtemp(prefix="pi-trigger-cwd-")
    print("scenarios: %d   repeats: %d   timeout: %ss" % (len(scenarios), args.repeats, args.timeout))
    print("sessions -> %s (isolated from ~/.pi/agent/sessions)" % session_dir)
    print("cwd      -> %s (neutral; no repo plan/CASE state in view)\n" % work_dir)

    rows = []
    started = time.time()
    try:
        for sc in scenarios:
            passes, notes = 0, []
            for i in range(args.repeats):
                tools, skills, results, err = run_once(sc, work_dir, session_dir, args.timeout)
                if err:
                    notes.append("run%d %s" % (i + 1, err))
                    continue
                ok, note = judge(sc, tools, skills, results)
                passes += 1 if ok else 0
                if not ok and note:
                    notes.append("run%d %s" % (i + 1, note))
            rate = 100.0 * passes / args.repeats
            rows.append((sc["id"], passes, args.repeats, rate, sc["why"], notes))
            print("%-28s %d/%d  %5.0f%%" % (sc["id"], passes, args.repeats, rate))
            for n in notes[:3]:
                print("      %s" % n[:150])
    finally:
        if not args.keep_sessions:
            shutil.rmtree(session_dir, ignore_errors=True)
        shutil.rmtree(work_dir, ignore_errors=True)

    total_pass = sum(r[1] for r in rows)
    total_runs = sum(r[2] for r in rows)

    if args.report:
        # A baseline is only useful if it survives the terminal it was printed
        # in. Append rather than overwrite so the history of prompt changes is
        # readable side by side.
        entry = {
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "repeats": args.repeats,
            "scenarios": {r[0]: {"pass": r[1], "of": r[2], "notes": r[5][:3]} for r in rows},
            "total_pass": total_pass,
            "total_runs": total_runs,
            "seconds": round(time.time() - started),
        }
        with open(args.report, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print("appended to %s" % args.report)
    print("\nTrigger rate: %d/%d (%.0f%%) in %.0fs"
          % (total_pass, total_runs, 100.0 * total_pass / max(total_runs, 1), time.time() - started))
    print("This is a baseline for future prompt changes. It cannot retroactively validate "
          "wording that was already changed before it existed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
