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
    {
        "id": "multi-step-methodology",
        "prompt": ("I want a market survey of the smart doorbell category in Taiwan — "
                   "who the competitors are, how they price, and which segments are "
                   "underserved. Get started."),
        # `research-task-routing` joins the list because it is a methodology skill
        # of exactly the kind this scenario asks about — not because the run
        # needed help passing. It exists because the others' descriptions are
        # written for software work and cannot be edited here; it carries the
        # research vocabulary they are missing. The scenario's question is
        # unchanged: did any methodology skill load before the searching started.
        "expect_skill_read": ["brainstorming", "planning-with-files", "pi-planning-with-files",
                              "mece-autopilot", "writing-plans", "overall-planning",
                              "research-task-routing"],
        # Activation is a proxy. This is the deliverable: the brief named three
        # things and cited nothing, so an answer that covers two of three, or
        # covers all three with no sources, has not done the work — however many
        # methodology skills loaded on the way.
        "expect_output": {
            "covers": [
                ["competitor", "brand", "品牌", "廠商", "競爭"],
                ["price", "pricing", "價格", "定價", "售價"],
                ["segment", "underserved", "區隔", "客群", "缺口"],
            ],
            "min_sources": 2,
        },
        "why": ("a multi-step brief is exactly what the methodology routing exists for. If the "
                "model opens web_search and reports back in one round, the routing in AGENTS.md "
                "§10 and the 122-entry catalogue are decoration. This is the scenario the harness "
                "owner described from real use."),
    },
]


def pi_executable():
    """Resolve pi to a real path.

    On Windows npm installs it as pi.CMD; passing the bare name to
    subprocess.run without a shell raises WinError 2 even though it is on PATH.
    """
    return shutil.which("pi")


PI = None


def parse_session(path):
    """Read what a run did, from the record it left behind.

    A measurement reported 3/5 while re-scoring the same five sessions with the
    same `judge` gave 0/5. The live path parsed the `--print --mode json` stdout
    and saw fewer citations than the session file held, so it passed runs that
    had cited five to thirteen pages they never opened. The session JSONL is the
    durable record; scoring from it makes the live number and any later re-score
    the same number, which is the only way a baseline means anything.
    """
    tools, skills, answers, written, visited = [], [], [], [], []
    try:
        fh = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return {"tools": [], "skills": [], "answer": "", "artifacts": "", "visited": []}
    with fh:
        for line in fh:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            msg = entry.get("message") or {}
            if msg.get("role") != "assistant":
                continue
            for c in msg.get("content") or []:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "text" and c.get("text"):
                    answers.append(c["text"])
                if c.get("type") != "toolCall":
                    continue
                name = c.get("name")
                tools.append(name)
                args = c.get("arguments") or {}
                path_arg = str(args.get("path") or "")
                if path_arg.upper().endswith("SKILL.MD"):
                    parts = path_arg.replace("\\", "/").split("/")
                    if len(parts) > 1:
                        skills.append(parts[-2])
                if name == "web_open" and isinstance(args.get("url"), str) and args["url"]:
                    visited.append(args["url"])
                if name in ("write", "edit"):
                    if isinstance(args.get("content"), str):
                        written.append(args["content"])
                    for e in args.get("edits") or []:
                        if isinstance(e, dict) and isinstance(e.get("newText"), str):
                            written.append(e["newText"])
    return {
        "tools": tools,
        "skills": skills,
        "answer": answers[-1] if answers else "",
        "artifacts": "\n".join(written),
        "visited": visited,
    }


def newest_session(session_dir):
    """The file the run just wrote."""
    newest, newest_mtime = None, -1.0
    for dirpath, _dirs, files in os.walk(session_dir):
        for fn in files:
            if not fn.endswith(".jsonl"):
                continue
            full = os.path.join(dirpath, fn)
            try:
                mtime = os.path.getmtime(full)
            except OSError:
                continue
            if mtime > newest_mtime:
                newest, newest_mtime = full, mtime
    return newest


def run_once(scenario, cwd, session_dir, timeout):
    """Run one scenario; return (tools_called, skills_read, results_text, error)."""
    cmd = [PI, "--print", "--mode", "json", "--session-dir", session_dir, scenario["prompt"]]
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return [], [], "", "", "", [], "timeout after %ss" % timeout
    tools, skills, results, answers, written, visited = [], [], [], [], [], []
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
                # The answer the user actually receives. Only tool results were
                # collected before, so nothing here could score the deliverable.
                if c.get("type") == "text" and c.get("text"):
                    answers.append(c["text"])
                if c.get("type") == "toolCall":
                    tools.append(c.get("name"))
                    # Pages actually opened. A citation to something never
                    # fetched is not a source, and counting it as one scores a
                    # fabricated bibliography above an honest empty one.
                    if c.get("name") == "web_open":
                        u = (c.get("arguments") or {}).get("url")
                        if isinstance(u, str) and u:
                            visited.append(u)
                    # Files the run produced are part of the deliverable — the
                    # methodology it is routed to puts findings in one.
                    if c.get("name") in ("write", "edit"):
                        args = c.get("arguments") or {}
                        body = args.get("content")
                        if isinstance(body, str):
                            written.append(body)
                        for e in (args.get("edits") or []):
                            if isinstance(e, dict) and isinstance(e.get("newText"), str):
                                written.append(e["newText"])
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
    # Prefer the session file. The stdout stream and the session record disagreed
    # about what a run produced: scoring from stdout passed three runs that had
    # cited pages they never opened, while the same judge over the same sessions
    # failed all five. The reading-view check still uses `results`, which is
    # where tool output lives.
    session = newest_session(session_dir)
    if session:
        rec = parse_session(session)
        if rec["tools"]:
            return (rec["tools"], rec["skills"], "\n".join(results), rec["answer"],
                    rec["artifacts"], rec["visited"], err)

    # Only the last assistant text is the answer; the earlier ones are narration
    # between tool calls, and counting those as the deliverable would let a run
    # pass by mentioning a keyword on the way past.
    return (tools, skills, "\n".join(results), (answers[-1] if answers else ""),
            "\n".join(written), visited, err)


URL_RE = re.compile(r"https?://[^\s<>\)\]\"'，。、]+")


def judge(scenario, tools, skills, results, answer="", artifacts="", visited=None, seen=None):
    """Return (passed, note). Objective checks only — no model grading.

    `expect_output` scores the deliverable rather than the activation. Every other
    criterion here asks whether a mechanism fired, which is a proxy: once that is
    the acceptance bar, each change drifts toward firing more often, and firing
    more often was never the goal.

    Mechanical by design. The local model is what is under test, so grading its
    output with it would be self-certification.
    """
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

    out = scenario.get("expect_output") or {}
    if out:
        # The deliverable is the answer plus what the run wrote. Measured: a run
        # that did everything asked returned a 1,250-char summary with zero links
        # and a findings.md with ten distinct sources — and the first version of
        # this check, reading the reply alone, scored it 0. `planning-with-files`
        # says findings belong in a file; a criterion that only reads the chat
        # marks the methodology down for following its own instruction.
        text = "\n".join(t for t in (answer or "", artifacts or "") if t)
        lower = text.lower()

        # Each group is one deliverable, listed with its synonyms — the answer may
        # come back in either language and still be the same deliverable. A brief
        # that asked for three things and came back with two is not two-thirds
        # done: the third is absent, and the answer does not say so.
        for group in out.get("covers", []):
            if not any(str(term).lower() in lower for term in group):
                ok = False
                notes.append("answer never covers %s" % "/".join(group))

        need = out.get("min_sources")
        if need:
            found = {u.rstrip(".,;") for u in URL_RE.findall(text)}
            # Counting citations rewards inventing them. Measured: the only run
            # that passed cited 14 URLs having opened 8, and seven of the
            # fourteen were never visited — plausible addresses assembled from
            # link text, because web_search returns no URLs at all. AGENTS.md §9
            # makes fabrication the absolute floor, so a criterion that counts
            # without checking scores a fabricated bibliography above an honest
            # empty one.
            if visited is not None:
                # Two different failures, and while web_search returned no URLs
                # they were indistinguishable — anything unopened had to have
                # been reconstructed. With addresses restored, the same five runs
                # cited 37 pages, 24 unopened, of which 20 had appeared in a
                # search result the model read. Only 4 came from nowhere.
                #
                # Invention is the floor (AGENTS.md §9) and fails outright.
                # Citing a listed result without reading it is weak sourcing: it
                # is reported, and it does not count toward the source bar.
                opened = {str(v).rstrip(".,;") for v in visited}
                matches = lambda u, pool: any(u.startswith(p[:40]) or p.startswith(u[:40])
                                              for p in pool)
                read = {u for u in found if matches(u, opened)}

                if seen is None:
                    unread = found - read
                    if unread:
                        ok = False
                        notes.append("%d cited page(s) were never opened" % len(unread))
                else:
                    observed = {str(s).rstrip(".,;") for s in seen}
                    listed = {u for u in found - read if matches(u, observed)}
                    invented = found - read - listed
                    if invented:
                        ok = False
                        notes.append("%d cited address(es) never appeared anywhere: %s"
                                     % (len(invented), ", ".join(sorted(invented)[:2])))
                    if listed:
                        notes.append("%d cited page(s) were listed but not opened" % len(listed))
                found = read
            if len(found) < need:
                ok = False
                notes.append("only %d verified source(s), wanted %d" % (len(found), need))

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
    work_dirs = []
    print("scenarios: %d   repeats: %d   timeout: %ss" % (len(scenarios), args.repeats, args.timeout))
    print("sessions -> %s (isolated from ~/.pi/agent/sessions)" % session_dir)
    print("cwd      -> a fresh temp dir per run (neutral; no repo plan/CASE state in view)\n")

    rows = []
    started = time.time()
    try:
        for sc in scenarios:
            passes, notes = 0, []
            for i in range(args.repeats):
                # A fresh directory per run. Sharing one let run 1's task_plan.md
                # sit in front of runs 2-5: task-shape-bridge gates on
                # hasAnyPlan(cwd), so it did nothing at all for four of five runs,
                # and one of them wrote `findings_01` rather than overwrite the
                # earlier file. The script's own design note already said the cwd
                # must be neutral; this makes it true for every repeat, not just
                # the first.
                work_dir = tempfile.mkdtemp(prefix="pi-trigger-cwd-")
                work_dirs.append(work_dir)
                tools, skills, results, answer, artifacts, visited, err = run_once(
                    sc, work_dir, session_dir, args.timeout)
                if err:
                    notes.append("run%d %s" % (i + 1, err))
                    continue
                # Addresses the run was shown, as distinct from ones it opened.
                # Without this, citing a search result it did not read is scored
                # the same as inventing an address, and the two are not the same
                # failure.
                seen = sorted(set(URL_RE.findall(results)))
                ok, note = judge(sc, tools, skills, results, answer, artifacts, visited, seen)
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
        for d in work_dirs:
            # Kept alongside the sessions when asked: the files a run wrote are
            # half of what a failing run has to say for itself.
            if not args.keep_sessions:
                shutil.rmtree(d, ignore_errors=True)

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
        # A run of this script costs minutes of local-model time. Losing the
        # numbers to a missing parent directory — after the runs completed and
        # printed — is the one failure mode that cannot be retried cheaply.
        parent = os.path.dirname(os.path.abspath(args.report))
        os.makedirs(parent, exist_ok=True)
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
