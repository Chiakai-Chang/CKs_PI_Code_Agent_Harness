#!/usr/bin/env python3
"""One screen that answers "what state is this harness in", in sixty seconds.

Written because the owner said 「我看不懂,沒辦法決定」 after two A/B runs. Forming
a view on one config flag required understanding ceiling effects, arm design,
the session-miner's marker table, and a 125-session inventory — five concepts
across three documents. That is not asking someone to decide; it is asking them
to take a course first.

Everything here is COMPUTED, never written down. A hand-maintained summary is a
lie within three weeks, and this repo has the scar: `global_dod.md` sat for
weeks as an unfilled template. Each number below names the query that produced
it so any line can be checked or disputed.

    python scripts/harness-status.py            # the screen
    python scripts/harness-status.py --verbose  # plus the per-guard breakdown

Reads only local session logs and repo files. No model, no network, seconds.
"""

from __future__ import annotations

import argparse
import collections
import glob
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SESSIONS = Path(os.path.expanduser("~")) / ".pi" / "agent" / "sessions"


def real_sessions():
    """Sessions from real work. Probe scratchpads and temp dirs are excluded:
    four of five probe runs once 'worked in the wrong project' purely because
    the workspace path carried the harness name."""
    return [f for f in glob.glob(str(SESSIONS / "*" / "*.jsonl"))
            if "Temp" not in f and "scratchpad" not in f.lower()]


def load_miner():
    spec = importlib.util.spec_from_file_location(
        "mine_session", ROOT / "scripts" / "mine-session.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scan(files):
    """One pass over every real session: calls, skill opens, harness touches,
    and which guards ever refused."""
    out = {
        "sessions": len(files), "calls": 0, "with_skill": set(),
        "harness_touch": 0, "other_calls": 0, "other_harness_touch": 0,
        "other_sessions": 0, "guards": collections.Counter(),
    }
    miner = load_miner()
    for f in files:
        own = "CKs" in f and "Harness" in f.replace("_", "-")
        if not own:
            out["other_sessions"] += 1
        try:
            rows = [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
        except Exception:
            continue
        blob = ""
        for r in rows:
            m = r.get("message")
            if not isinstance(m, dict):
                continue
            if m.get("role") == "assistant":
                for b in (m.get("content") or []):
                    if isinstance(b, dict) and b.get("type") == "toolCall":
                        a = json.dumps(b.get("arguments"), ensure_ascii=False)
                        out["calls"] += 1
                        if not own:
                            out["other_calls"] += 1
                        if re.search(r"[\\/][\w.-]+[\\/]SKILL\.md", a):
                            out["with_skill"].add(f)
                        if "CKs_PI_Code_Agent_Harness" in a:
                            out["harness_touch"] += 1
                            if not own:
                                out["other_harness_touch"] += 1
            else:
                blob += json.dumps(m, ensure_ascii=False)
        for label, marker in miner.REFUSALS:
            if marker in blob:
                out["guards"][label] += 1
    out["guard_names"] = [l for l, _m in miner.REFUSALS]
    return out


def plan_order():
    """The owner's actual complaint, as a number."""
    try:
        p = subprocess.run([sys.executable, str(ROOT / "scripts" / "report-plan-order.py"),
                            "--all"], capture_output=True, text=True, timeout=300,
                           encoding="utf-8", errors="replace")
        m = re.search(r"no-plan\s+(\d+)\s+([\d.]+)%", p.stdout)
        n = re.search(r"sessions that searched at least once:\s*(\d+)", p.stdout)
        return (int(n.group(1)) if n else None, float(m.group(2)) if m else None)
    except Exception:
        return (None, None)


def suite():
    """Whether the tests pass, from an actual run — not from memory."""
    try:
        p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                           capture_output=True, text=True, cwd=str(ROOT), timeout=900,
                           encoding="utf-8", errors="replace")
        m = re.search(r"Ran (\d+) tests", p.stderr + p.stdout)
        return (int(m.group(1)) if m else None, p.returncode == 0)
    except Exception:
        return (None, None)


def unproven():
    """Items the ledger marks shipped-but-unproven or measure-first, counted
    from PROGRESS.md so the two cannot drift apart.

    The markers are read from the file but never PRINTED: this script has to run
    on the owner's default Windows console, which is cp950, and an emoji there is
    a UnicodeEncodeError, not a cosmetic problem. Caught on the first run."""
    text = (ROOT / "PROGRESS.md").read_text(encoding="utf-8")
    return (len(re.findall(r"^### 🟡", text, re.M)),
            len(re.findall(r"^### 🔴", text, re.M)))


def _safe_print(*parts):
    """Print, or degrade — never crash.

    The owner's default Windows console is cp950. The first run of this script
    died on an emoji AFTER printing most of the screen, which is the worst
    possible failure for a status page: it looks like the harness is broken when
    only the last line was unprintable."""
    text = " ".join(str(p) for p in parts)
    try:
        # NOT _safe_print here: a blanket rename once turned this into infinite
        # recursion, and the cp950 test run is what caught it.
        print(text)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "ascii"
        print(text.encode(enc, "replace").decode(enc, "replace"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--skip-tests", action="store_true",
                    help="skip the unittest run (it takes ~2 minutes)")
    args = ap.parse_args(argv)

    files = real_sessions()
    s = scan(files)
    silent = [g for g in s["guard_names"] if not s["guards"][g]]
    fired = [(g, s["guards"][g]) for g in s["guard_names"] if s["guards"][g]]
    n_sessions, no_plan = plan_order()
    yellow, red = unproven()

    _safe_print("=" * 66)
    _safe_print(" CK's Pi Code Agent Harness — 現況(全部由查詢算出,非手寫)")
    _safe_print("=" * 66)

    _safe_print("\n■ 這個 harness 有沒有在幫忙")
    pct = (len(s['with_skill']) * 100 // s['sessions']) if s["sessions"] else 0
    _safe_print(f"  技能被打開過的 session   {len(s['with_skill']):4} / {s['sessions']:<4} ({pct}%)")
    if no_plan is not None:
        _safe_print(f"  開始工作前沒有計畫       {no_plan:.0f}%   （{n_sessions} 個有搜尋的 session）")
        _safe_print( "                           ← 這是擁有者原本抱怨的那件事")
    if s["other_sessions"]:
        op = s["other_harness_touch"] * 100 // max(s["other_calls"], 1)
        _safe_print(f"  在別的專案工作時,呼叫    {op}%   跑進 harness 目錄"
              f"（{s['other_harness_touch']}/{s['other_calls']}）")

    _safe_print("\n■ 守衛:裝了幾個,動了幾個")
    _safe_print(f"  真實 session             {s['sessions']}")
    _safe_print(f"  會拒絕的守衛             {len(s['guard_names'])}")
    _safe_print(f"  **從未觸發過**           {len(silent)}")
    if fired:
        top = ", ".join(f"{g}({n})" for g, n in sorted(fired, key=lambda x: -x[1])[:4])
        _safe_print(f"  觸發最多                 {top}")
    if args.verbose:
        _safe_print("\n  從未觸發的:")
        for g in silent:
            _safe_print(f"    - {g}")

    _safe_print("\n■ 帳本上還沒有結論的")
    _safe_print(f"  已上線但效果未證明       {yellow}")
    _safe_print(f"  先量再決定               {red}")

    if not args.skip_tests:
        n, ok = suite()
        _safe_print("\n■ 這一份程式碼本身")
        _safe_print(f"  測試                     {n} 條,{'通過' if ok else '**失敗**'}")

    _safe_print("\n" + "-" * 66)
    _safe_print("每一行的來源:")
    _safe_print("  技能／harness 觸碰  ~/.pi/agent/sessions 全掃(排除探針)")
    _safe_print("  沒有計畫            scripts/report-plan-order.py --all")
    _safe_print("  守衛觸發            scripts/mine-session.py 的 marker 表")
    _safe_print("  未證明項目          PROGRESS.md 的狀態標記")
    _safe_print("  測試                python -m unittest discover -s tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
