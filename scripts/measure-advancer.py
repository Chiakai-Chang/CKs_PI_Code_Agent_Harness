#!/usr/bin/env python3
"""Measure whether the C.A.S.E. loop drives a task to completion, on real runs.

Usage:
    python scripts/measure-advancer.py --runs 3 --prompt baseline
    python scripts/measure-advancer.py --runs 1 --prompt research
    python scripts/measure-advancer.py --self-check     # prove it can fail

Slow: each run launches Pi against the local model. NOT in CI.

This exists because the 2026-08-06 verdict ("keep enableCaseAdvancer false")
rested on three defects that are now fixed - the advancer judged stalls by
counting its own injections, it wrote ESCALATED into the task's status, and cwd
confusion consumed two of five runs. The verdict has to be re-earned on the
repaired foundation rather than inherited.

Three things this script does because the last measurement got them wrong:

* **Counts by field, not by substring.** Counting `case-advance` with grep over
  raw JSONL once reported zero injections when there were four, and the run was
  one step from being escalated on that number. Every count here filters on
  `message.role` / `toolName` / `customType`.
* **Counts `edit` as a status write.** A run reported "0 status writes" while
  the status had moved six times, because only `write` was counted. That number
  read as "the guard was bypassed" - the opposite of the truth.
* **Polls for file growth instead of waiting for a timeout.** "540 seconds with
  no session file" was written up as a hang; the run finished in 3m14s and
  reached REVIEW. A timeout measures the observer's patience.

Each run gets its own temp directory. Sharing one made four of five runs measure
something other than what they claimed, and the tell (`findings_01`) was sitting
in the output the whole time.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROMPTS = {
    # Verbatim from docs/measurements/2026-08-06-advancer-verdict.md so the
    # numbers are comparable. A reworded prompt is a different experiment.
    "baseline": "這個專案是什麼?簡短說明就好。",
    # Verbatim from docs/measurements/2026-08-06-depth-and-artifact-gates-live.md.
    # The owner's complaint is about research sessions, and a trivial task
    # cannot answer it.
    "research": (
        "我要一份速查表:列出這 15 個工具各自的最新穩定版本號 —— "
        "Node.js、Python、Go、Rust、Deno、Bun、TypeScript、Vite、PostgreSQL、"
        "Redis、Docker、Kubernetes、Nginx、Terraform、Ansible。只要版本號,不用細節說明。"
    ),
}

STATUS_NAMES = ("status.txt",)


def session_records(session_dir: Path):
    """Every message a session recorded, unwrapped from its envelope.

    The envelope matters and cost a run to learn. Records are
    `{"type": "message", "message": {"role": ..., "content": [...]}}`, plus
    `session` / `model_change` / `thinking_level_change` lines that carry no
    message at all. Reading `role` off the top level returns None for every
    line, so the first real run reported zero tool calls against an 11 KB
    session — a clean set of zeroes that looked like "the advancer never fired"
    and was really "the parser never matched".

    The self-check did not catch it because its fixture was written from
    memory. Fixtures that invent the payload pass while the thing they stand
    for is broken; this one is now built from records copied out of session
    019fdebe.
    """
    for path in sorted(session_dir.rglob("*.jsonl")):
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(rec, dict) and rec.get("type") == "message":
                    msg = rec.get("message")
                    if isinstance(msg, dict):
                        yield msg
                elif isinstance(rec, dict) and rec.get("type") == "custom_message":
                    # An injection has NO `role` field at all — it is
                    # `{"type": "custom_message", "customType": ..., "content": ...}`.
                    # Filtering on `role` made both injection counters
                    # structurally incapable of returning anything but zero,
                    # and three baseline runs reported "0 injections" before
                    # this was checked against a session known to contain one.
                    yield rec
                elif isinstance(rec, dict) and "role" in rec:
                    yield rec


def tally(session_dir: Path) -> dict:
    """Counts taken from record fields.

    `write` and `edit` both change a file. Counting only `write` produced a
    zero that read as "the tool-first guard was bypassed" when the guard had in
    fact worked - the model had used `edit`.
    """
    counts = {
        "tool_calls": 0,
        "blocked": 0,
        "advance_injections": 0,
        "blocked_claim_injections": 0,
        "status_writes_tool": 0,
        "status_writes_bash": 0,
        "assistant_turns": 0,
    }
    for rec in session_records(session_dir):
        role = rec.get("role")
        if role == "assistant":
            counts["assistant_turns"] += 1
            for block in rec.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "toolCall":
                    counts["tool_calls"] += 1
                    name = str(block.get("name") or block.get("toolName") or "")
                    args = block.get("arguments") or block.get("input") or {}
                    if not isinstance(args, dict):
                        continue
                    if name in ("write", "edit"):
                        path = str(args.get("path") or args.get("file_path") or "")
                        if any(path.endswith(s) for s in STATUS_NAMES):
                            counts["status_writes_tool"] += 1
                    elif name == "bash":
                        cmd = str(args.get("command") or "")
                        if any(s in cmd for s in STATUS_NAMES) and (">" in cmd or "tee" in cmd):
                            counts["status_writes_bash"] += 1
        elif role == "toolResult":
            if rec.get("isError"):
                counts["blocked"] += 1
        elif rec.get("type") == "custom_message" or rec.get("customType"):
            ct = str(rec.get("customType") or "")
            if ct == "case-advance":
                counts["advance_injections"] += 1
            elif ct == "blocked-claim":
                counts["blocked_claim_injections"] += 1
    return counts


def read_status(task_dir: Path) -> str:
    p = task_dir / "status.txt"
    try:
        return p.read_text(encoding="utf-8").strip()
    except OSError:
        return "<missing>"


BOOTSTRAP = ROOT / "external" / "Local-Agent-Workspace" / "scripts" / "bootstrap.py"


def make_fixture(base: Path, claim_turns: int = 0) -> Path:
    """A real C.A.S.E. project with one PENDING task, outside this repository.

    Outside on purpose: the flag is global once restored, and a queue left
    inside the harness became a decoy that consumed an entire run.

    Bootstrapped rather than hand-built, and that distinction is the whole
    reason this function has a docstring. The first version created only
    `02_Task_Queue/Task_001_probe/`, which looks like a C.A.S.E. project and is
    not one: `isCaseProject()` asks for `CASE.md` or `00_Constitution`, so the
    advancer returned before doing anything in all three runs. The phase gate
    fired in the same runs because it keys on the queue directory alone — one
    guard speaking and the other silent read like a bridge defect and was a
    fixture defect.

    Third time today that a hand-built fixture agreed with my expectations
    instead of with the system.
    """
    subprocess.run(["git", "init", "-q"], cwd=base, check=True)
    subprocess.run([sys.executable, str(BOOTSTRAP), str(base)],
                   check=True, capture_output=True)
    # Scope the flag to THIS fixture instead of switching it on globally.
    #
    # Until 2026-08-08 a measurement meant editing pi-config/harness-config.json
    # and running restore, which drove every other C.A.S.E. project the user had
    # open for the duration. Task_019 added a per-project resolver; using it here
    # is also the first live exercise of it, which is the difference between a
    # mechanism that passes its unit tests and one that has fired.
    local = {"enableCaseAdvancer": True}
    if claim_turns:
        # The experiment lives here, not in a shipped constant. resolveFlag
        # refuses anything below the default or above 12, so this can only
        # tighten the gate.
        local["caseClaimRefusalTurns"] = claim_turns
    (base / ".pi-harness.json").write_text(
        json.dumps(local, indent=2), encoding="utf-8")
    task = base / "02_Task_Queue" / "Task_001_probe"
    task.mkdir(parents=True, exist_ok=True)
    (task / "status.txt").write_text("PENDING", encoding="utf-8")
    (task / "role.md").write_text(
        "# Role\n\nWorker. 回答使用者的問題,並照 C.A.S.E. 流程留下紀錄。\n",
        encoding="utf-8")
    (task / "recipe.md").write_text(
        "# Recipe\n\n## Objective\n\n回答使用者的問題。\n\n"
        "## Local Definition of Done\n\n- [ ] 回答寫進 output.md\n- [ ] retro.md 有四節\n",
        encoding="utf-8")
    if not (base / ".pi-harness.json").exists():
        raise SystemExit(f"FATAL: {base} has no .pi-harness.json — the advancer "
                         f"would be off and the run would measure nothing.")
    # Assert the precondition instead of discovering it in the results. The
    # advancer checks exactly this, and a fixture that fails it produces a
    # clean page of zeroes that reads as a finding.
    if not ((base / "CASE.md").exists() or (base / "00_Constitution").exists()):
        raise SystemExit(
            f"FATAL: {base} is not a C.A.S.E. project — no CASE.md and no "
            f"00_Constitution, so isCaseProject() is false and the advancer "
            f"will return before it does anything. Measuring here would report "
            f"zero injections and mean nothing.")
    return task


def poll_until_done(proc, session_dir: Path, task_dir: Path, limit_s: int, quiet_s: int):
    """Watch the session file grow. Stop when it stops growing, not on a clock.

    A run that produces nothing for ten minutes and a run that is thinking look
    identical to a timeout. They do not look identical to a file that is getting
    longer.
    """
    started = time.time()
    last_size, last_change = -1, time.time()
    # Time from launch to the FIRST byte of session, recorded on every run.
    #
    # The quiet threshold was derived from gaps INSIDE a running session
    # (median 1s, p95 190s, max 237s) and then applied to the opening, where
    # nothing is written until the first response — a parameter tuned against
    # the wrong distribution, which looks evidence-based and still cuts runs
    # off. This is the distribution that governs the opening, and collecting it
    # as a by-product means never having to spend a run measuring it.
    first_record_at = None
    while proc.poll() is None:
        size = sum(p.stat().st_size for p in session_dir.rglob("*.jsonl")) if session_dir.exists() else 0
        now = time.time()
        if size != last_size:
            if last_size <= 0 and size > 0 and first_record_at is None:
                first_record_at = now - started
                print(f"    first record after {first_record_at:.0f}s")
            last_size, last_change = size, now
            print(f"    [{int(now - started):>4}s] {size:>7} bytes  status={read_status(task_dir)}")
        if now - last_change > quiet_s:
            where = "before the first record" if first_record_at is None else "mid-run"
            print(f"    quiet for {quiet_s}s {where} — stopping")
            stop_tree(proc)
            return ("quiet-startup" if first_record_at is None else "quiet"), first_record_at
        if now - started > limit_s:
            print(f"    hit the {limit_s}s ceiling — stopping")
            stop_tree(proc)
            return "ceiling", first_record_at
        time.sleep(5)
    return "finished", first_record_at



def stop_tree(proc) -> None:
    """Kill the process AND its children, then verify nothing survived.

    `pi` resolves to `pi.CMD` on Windows, so the launch goes through a shell and
    `proc.terminate()` reaches the cmd.exe wrapper only. The node process
    underneath survives and keeps generating against the local model server.

    Measured 2026-08-09, because the owner noticed the model was still busy
    while nothing was running here: two orphaned `pi --print` processes from
    runs this script had "terminated" the night before were still alive, still
    holding slots on the server, and therefore still competing with every later
    measurement. Two runs that reported "quiet for 180s" were racing orphans
    they had themselves created.

    The repo already carried this scar in another form: on Windows spawn()
    hands back the launcher, so what has to be asserted is killability, not pid
    equality.
    """
    if proc.poll() is not None:
        return
    if os.name == "nt":
        # taskkill /T walks the tree; terminate() does not.
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True)
    else:
        proc.terminate()
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()


def orphan_pids() -> list:
    """Live `pi --print` processes, whoever started them.

    Run before and after a measurement: one left over from earlier is not a
    curiosity, it is another client on the same model server and every number
    taken beside it is suspect.

    PowerShell CIM rather than `wmic`. The first version used wmic, which does
    not exist on this machine at all — so the guard could only ever return an
    empty list and could never fire. That is the exact class
    `check-guard-mutations` was built for, written the same day, by me.
    """
    if os.name != "nt":
        return []
    script = (
        "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | "
        "Where-Object { $_.CommandLine -like '*pi-coding-agent*' -and "
        "$_.CommandLine -like '*--print*' } | "
        "ForEach-Object { $_.ProcessId }"
    )
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                             capture_output=True, text=True, errors="replace",
                             timeout=60).stdout
    except Exception:
        # Unknowable is not the same as none: say so rather than report clean.
        print("    WARNING: could not enumerate processes; orphan check did NOT run")
        return []
    return [int(t) for t in out.split() if t.isdigit()]


def one_run(prompt_key: str, index: int, limit_s: int, quiet_s: int, claim_turns: int = 0) -> dict:
    base = Path(tempfile.mkdtemp(prefix=f"advancer-{prompt_key}-{index}-"))
    task = make_fixture(base, claim_turns)
    session_dir = base / ".sess"
    print(f"\n=== run {index} ({prompt_key})  {base}")
    # The resolved path, not the bare name: on Windows `pi` is `pi.CMD`, which
    # `shutil.which` finds and `CreateProcess` refuses. The check passing and
    # the launch failing is the same gap this repo keeps meeting - "it is on
    # PATH" is not "it will start".
    exe = shutil.which("pi")
    proc = subprocess.Popen(
        [exe, "--print", "--session-dir", str(session_dir), PROMPTS[prompt_key]],
        # Kept, not discarded. Two runs produced zero turns and zero tool calls
        # and the reason was unavailable because both streams went to DEVNULL —
        # an instrument that hides the failure it is measuring. 2026-08-09.
        cwd=str(base), stdout=open(base / "pi-stdout.log", "wb"),
        stderr=open(base / "pi-stderr.log", "wb"),
        shell=exe.lower().endswith((".cmd", ".bat")),
    )
    how, first_record_s = poll_until_done(proc, session_dir, task, limit_s, quiet_s)
    stop_tree(proc)
    left = orphan_pids()
    if left:
        print(f"    WARNING: {len(left)} pi process(es) still alive after stop: {left}")
    counts = tally(session_dir) if session_dir.exists() else {}
    result = {"run": index, "prompt": prompt_key, "ended": how,
              "first_record_s": (round(first_record_s) if first_record_s else None),
              "status": read_status(task),
              "files": sorted(p.name for p in task.iterdir()),
              "dir": str(base), **counts}
    print("    " + json.dumps({k: v for k, v in result.items() if k != "dir"}, ensure_ascii=False))
    return result


def self_check() -> int:
    """Break the counters on purpose and require the numbers to move.

    The previous measurement script reported a zero twice, each time on a
    metric that would have inverted the conclusion, and both were found by
    accident. A counter nobody has seen fail is a counter nobody should quote.
    """
    fake = Path(tempfile.mkdtemp(prefix="advancer-selfcheck-"))
    sess = fake / ".sess"
    sess.mkdir(parents=True)
    # Wrapped exactly as Pi writes them, copied from session 019fdebe: message
    # records carry a `type` and nest the message one level down, and the file
    # also holds `session` / `model_change` lines with no message at all. The
    # first version of this fixture wrote bare `{"role": ...}` objects from
    # memory, passed, and hid a parser that matched nothing — an 11 KB session
    # tallied as all zeroes, which reads as "the advancer never fired".
    def msg(m):
        return {"type": "message", "id": "x", "timestamp": "t", "message": m}

    records = [
        {"type": "session", "cwd": "/tmp/x", "version": 1},
        {"type": "model_change", "modelId": "probe"},
        msg({"role": "assistant", "content": [
            {"type": "thinking", "text": "..."},
            {"type": "toolCall", "id": "a", "name": "write",
             "arguments": {"path": "02_Task_Queue/Task_001_probe/status.txt"}}]}),
        msg({"role": "assistant", "content": [
            {"type": "toolCall", "id": "b", "name": "edit",
             "arguments": {"path": "02_Task_Queue/Task_001_probe/status.txt"}}]}),
        msg({"role": "assistant", "content": [
            {"type": "toolCall", "id": "c", "name": "bash",
             "arguments": {"command": "printf DONE > 02_Task_Queue/Task_001_probe/status.txt"}}]}),
        msg({"role": "assistant", "content": [
            {"type": "toolCall", "id": "d", "name": "bash",
             "arguments": {"command": "cat 02_Task_Queue/Task_001_probe/status.txt"}}]}),
        msg({"role": "toolResult", "isError": True, "toolName": "bash",
             "toolCallId": "c", "content": [{"type": "text", "text": "refused"}]}),
        {"role": "custom", "customType": "case-advance"},
        {"role": "custom", "customType": "blocked-claim"},
    ]
    with open(sess / "probe.jsonl", "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    got = tally(sess)
    expected = {
        "tool_calls": 4,
        "blocked": 1,
        "advance_injections": 1,
        "blocked_claim_injections": 1,
        # write + edit. Counting only `write` gives 1, which is the exact
        # under-count that once read as "the guard was bypassed".
        "status_writes_tool": 2,
        # `cat status.txt` is a read. Counting it gave a number that nearly
        # inverted the headline.
        "status_writes_bash": 1,
        "assistant_turns": 4,
    }
    shutil.rmtree(fake, ignore_errors=True)
    bad = {k: (got.get(k), v) for k, v in expected.items() if got.get(k) != v}
    if bad:
        print("SELF-CHECK FAILED — counters disagree with the hand-built fixture:")
        for k, (g, e) in bad.items():
            print(f"  {k}: got {g}, expected {e}")
        return 1
    print("self-check: 7 counters agree with a fixture built by hand, including")
    print("  the two that were wrong last time (edit counts; `cat` does not).")
    return 0



def report_status() -> int:
    """What is running right now, and whether anyone still owns it.

    Asked for after the third time a live model with a silent shell caused
    confusion. Two situations look identical from outside — a measurement I
    launched detached, and a process leaked by one I thought I had stopped —
    and until now only a hand-written PowerShell query could tell them apart.
    The owner should not have to be the detector.
    """
    pids = orphan_pids()
    if not pids:
        print("no `pi --print` running.")
        return 0
    for pid in pids:
        script = ("Get-CimInstance Win32_Process -Filter 'ProcessId=%d' | "
                  "ForEach-Object { $_.ParentProcessId }" % pid)
        out = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                             capture_output=True, text=True, errors="replace").stdout
        parent = next((int(t) for t in out.split() if t.isdigit()), None)
        alive = False
        if parent:
            chk = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-Process -Id %d -ErrorAction SilentlyContinue | "
                 "ForEach-Object { $_.Id }" % parent],
                capture_output=True, text=True, errors="replace").stdout
            alive = str(parent) in chk
        owner = f"parent {parent} alive — a running measurement" if alive else                 "PARENT DEAD — an orphan, stop it: taskkill /PID %d /T /F" % pid
        print(f"pi pid {pid}: {owner}")
    # Progress of the newest fixture, so "is it working" has an answer too.
    import glob
    dirs = sorted(glob.glob(os.path.join(tempfile.gettempdir(), "advancer-*")),
                  key=os.path.getmtime)
    if dirs:
        newest = Path(dirs[-1])
        size = sum(p.stat().st_size for p in (newest / ".sess").rglob("*.jsonl"))             if (newest / ".sess").exists() else 0
        task = newest / "02_Task_Queue" / "Task_001_probe"
        print(f"newest fixture {newest.name}: session {size} bytes, "
              f"status={read_status(task)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Measure the C.A.S.E. advancer on real runs.")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--prompt", choices=sorted(PROMPTS), default="baseline")
    # Both defaults come from the gap distribution of a run that COMPLETED a
    # claim and 22 searches (session 019fdf..., 74 records): median gap 1s, p95
    # 190s, max 237s. The old quiet default of 180s sat below both the p95 and
    # the max, so it was guaranteed to cut legitimate runs short — and it did,
    # twice, producing "0 claims" that were the instrument's answer rather than
    # the model's. 600s is ~2.5x the observed max. The old 900s limit was below
    # the length of the only run that got anywhere.
    ap.add_argument("--limit", type=int, default=2400, help="seconds per run before giving up")
    ap.add_argument("--quiet", type=int, default=600, help="seconds of no file growth before giving up")
    ap.add_argument("--out", help="write the results as JSON here")
    ap.add_argument("--claim-turns", type=int, default=0,
                    help="tighten the CLAIM exit ramp for the fixture only (4-12)")
    ap.add_argument("--status", action="store_true",
                    help="report what is running right now, and whether it is mine")
    ap.add_argument("--self-check", action="store_true", help="prove the counters can fail")
    args = ap.parse_args()

    if args.status:
        return report_status()

    if args.self_check:
        return self_check()

    if self_check() != 0:
        print("refusing to measure with counters that do not agree with a known fixture")
        return 2

    if not shutil.which("pi"):
        print("FAIL: `pi` is not on PATH")
        return 2

    # Refuse to measure beside another client of the same model server.
    #
    # 2026-08-09: two orphaned `pi --print` processes from the previous night
    # were still holding slots, and the runs taken beside them reported "quiet
    # for 180s" — a number produced by contention, not by the harness. A
    # measurement with an unknown second consumer is not a measurement.
    stale = orphan_pids()
    if stale:
        print(f"FAIL: {len(stale)} `pi --print` process(es) already running: {stale}")
        print("Any number taken beside them is contended. Stop them first:")
        print("  taskkill /PID <pid> /T /F")
        return 2

    results = [one_run(args.prompt, i + 1, args.limit, args.quiet, args.claim_turns)
               for i in range(args.runs)]
    if args.out:
        Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nwrote {args.out}")
    reached = [r for r in results if r["status"] in ("REVIEW", "DONE")]
    print(f"\n{len(reached)}/{len(results)} runs reached REVIEW or DONE.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
