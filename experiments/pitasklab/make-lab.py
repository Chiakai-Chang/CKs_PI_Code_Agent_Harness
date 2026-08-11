#!/usr/bin/env python3
"""Rebuild the PiTaskLab experiment site from scratch, deterministically.

    python experiments/pitasklab/make-lab.py --out D:/MyProject/PiTaskLab

Why this file exists: every number reported for T-A1, T-A3 and T-A6 on
2026-08-11 — 11/11 five times, 9/9 once, 57 tool calls against 23-33 — was
produced against a task package that lived only on a removable disk, scored by
two scripts that lived in `/tmp` and a session scratchpad. The repo's own rule is
that a probe fixture must be rebuildable from a committed source, and it was not.
This is that source.

The site is deliberately OUTSIDE the harness repo. Four earlier probe runs were
invalidated because their working directory carried the harness name and the
model went to work on the harness instead of the task; measured afterwards, the
owner's real sessions touched the harness once in 228 calls. The path must not
say "harness".

Ground truth is written INTO the site as dotfiles and must stay out of the
model's way — the site's own `.gitignore` covers them, and the site is not a git
repository by default anyway. The answers are recomputed here every time, so a
lost site costs one command, not a day.
"""

import argparse
import hashlib
import io
import json
import os

SERVICE_NAMES = [
    "auth-gateway", "billing", "catalog", "checkout", "delivery", "email",
    "fraud", "inventory", "ledger", "notify", "pricing", "profile", "ratings",
    "search", "shipping", "support",
]

# Task_001: eight services, two deviations per field. The answer is precomputed
# so scoring never reads what the model wrote and calls it the truth.
TASK1 = {
    "svc-01": (3000, 3), "svc-02": (3000, 3), "svc-03": (9000, 3),
    "svc-04": (3000, 7), "svc-05": (3000, 3), "svc-06": (12000, 3),
    "svc-07": (3000, 3), "svc-08": (3000, 11),
}

# Task_002: one seeded defect per listed service, each with exactly one correct
# repair stated by the rule that reports it.
TASK2_DEFECTS = {
    "svc-02": "id",           "svc-03": "owner",
    "svc-05": "timeout_mult", "svc-06": "endpoint",
    "svc-08": "timeout_range", "svc-09": "retries",
    "svc-11": "missing",      "svc-12": "owner",
    "svc-14": "timeout_mult", "svc-15": "endpoint",
    "svc-16": "retries",
}

HERE = os.path.dirname(os.path.abspath(__file__))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)


def dump(path, obj):
    write(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def build_task1(out):
    for i, (sid, (timeout, retries)) in enumerate(sorted(TASK1.items()), start=1):
        dump(os.path.join(out, "data", "%s.json" % sid), {
            "id": sid, "name": SERVICE_NAMES[i - 1], "owner": "team-%s" % "abcdefgh"[i % 8],
            "timeout_ms": timeout, "retries": retries,
        })
    dump(os.path.join(out, ".ground-truth.json"), {
        "common_timeout_ms": 3000,
        "common_retries": 3,
        "odd_timeout": sorted(s for s, (t, _) in TASK1.items() if t != 3000),
        "odd_retries": sorted(s for s, (_, r) in TASK1.items() if r != 3),
    })


def build_task2(out):
    teams, expected = {}, {}
    for i, name in enumerate(SERVICE_NAMES, start=1):
        sid = "svc-%02d" % i
        owner = "team-%s" % "abcdefgh"[i % 8]
        teams[sid] = owner
        good = {"id": sid, "name": name, "owner": owner,
                "endpoint": "https://%s.internal.invalid/v1" % name,
                "timeout_ms": 3000, "retries": 3}
        expected[sid] = dict(good)
        broken = dict(good)
        kind = TASK2_DEFECTS.get(sid)
        if kind == "id":
            broken["id"] = sid.replace("svc-", "service-")
        elif kind == "owner":
            broken["owner"] = "team-legacy"
        elif kind == "timeout_mult":
            broken["timeout_ms"] = 3200          # rounds to 3000
        elif kind == "timeout_range":
            broken["timeout_ms"] = 45000
            expected[sid]["timeout_ms"] = 10000  # clamps to the boundary
        elif kind == "retries":
            broken["retries"] = 9
            expected[sid]["retries"] = 5
        elif kind == "endpoint":
            broken["endpoint"] = good["endpoint"].replace("https://", "http://")
        elif kind == "missing":
            del broken["retries"]                # defaults.json says 3
        dump(os.path.join(out, "services", "%s.json" % sid), broken)
    dump(os.path.join(out, "teams.json"), teams)
    dump(os.path.join(out, "defaults.json"), {
        "owner": "team-unassigned", "endpoint": "https://internal.invalid/",
        "timeout_ms": 3000, "retries": 3,
    })
    dump(os.path.join(out, ".ground-truth-002.json"),
         {"expected": expected, "defects": {k: ["", v] for k, v in TASK2_DEFECTS.items()}})
    write(os.path.join(out, "check.py"),
          io.open(os.path.join(HERE, "check.py"), encoding="utf-8").read())
    # The tools the task must not touch, hashed BEFORE any run. Captured here
    # rather than by the scorer: a baseline taken after the fact would call
    # whatever the model left behind "unchanged".
    lines = []
    for name in ("check.py", "teams.json", "defaults.json"):
        raw = io.open(os.path.join(out, name), "rb").read()
        lines.append("%s  %s" % (hashlib.sha256(raw).hexdigest(), name))
    write(os.path.join(out, ".baseline-002.txt"), "\n".join(lines) + "\n")


def copy_packages(out):
    """Constitution, roadmap and the two task packages, verbatim from `site/`."""
    src = os.path.join(HERE, "site")
    for root, _dirs, files in os.walk(src):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, src)
            write(os.path.join(out, rel), io.open(full, encoding="utf-8").read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="site directory; must NOT contain 'harness'")
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    if "harness" in out.lower():
        raise SystemExit("refusing: the path contains 'harness', which is the "
                         "confound that invalidated four earlier probe runs")
    copy_packages(out)
    build_task1(out)
    build_task2(out)
    write(os.path.join(out, ".gitignore"), ".ground-truth*.json\nrun*.log\n")
    print("site rebuilt at %s" % out)
    print("  Task_001_ConfigDrift  -> data/, .ground-truth.json")
    print("  Task_002_ConfigRepair -> services/, check.py, teams.json, defaults.json")
    print("run:  cd %s && pi --print '請處理 02_Task_Queue 裡待辦的任務' < /dev/null" % out)
    print("score: python %s/score_task00N.py <report.txt>   (from the site)" % HERE)


if __name__ == "__main__":
    main()
