#!/usr/bin/env python3
"""Hold the prior-art register to the sources it claims to cover.

Why this exists, in one measured example. On 2026-08-06 a queue advancer was
built on `turn_end` with a retirement counter over injections, and a five-run
measurement then discovered that both choices were wrong. Our own notes, written
weeks earlier and sitting in `docs/superpowers/pi-until-done-learnings/`, say
that `agent_settled` owns automatic continuation and that the spin guard keys on
progress signals. The reference clone implementing exactly that was already on
disk.

Cloning is not reviewing and reviewing is not remembering. So the register is
checked rather than merely written:

  * every source declared in `external-manifest.json` has a row;
  * every clone sitting under `research/` or `reference/` is a declared source,
    so a stray clone cannot accumulate unnoticed;
  * every learnings document a row points at exists.

It also prints how many sources have never been reviewed. That number is the
uncomfortable one, and it is the reason the file exists.

Zero dependencies, standard library only.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = "external-manifest.json"
README = "README.md"
REGISTER = os.path.join("docs", "prior-art", "REGISTER.md")
CLONE_DIRS = ("research", "reference")

# Repositories that are this project or the engine it extends, not prior art.
SELF = {"cks_pi_code_agent_harness", "pi-mono"}

REVIEWED = "已審視"
UNREVIEWED = "未審視"


def manifest_sources(root):
    path = os.path.join(root, MANIFEST)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    found = []

    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            if "name" in node and ("path" in node or "url" in node):
                found.append(node)
            else:
                for value in node.values():
                    walk(value)

    walk(data)
    return found


def readme_repos(root):
    """Repositories README links to.

    README is the list the project's owner reads and remembers, so it is a
    source of truth in its own right — not a rendering of the manifest. Building
    the register from the manifest alone was the first version's mistake, and it
    hid the sharpest fact available: `pi-until-done`, the clone that already
    implements the continuation loop and the evidence judge this project spent a
    day rebuilding, is linked nowhere in README.
    """
    path = os.path.join(root, README)
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        text = f.read()
    found = set()
    for _owner, repo in re.findall(r"https://github\.(?:com|alchaincyf)/([\w.-]+)/([\w.-]+)", text):
        name = repo.rstrip("/").removesuffix(".git")
        if name.lower() not in SELF:
            found.add(name)
    return found


def normalise(name):
    return name.removesuffix(".git").lower()


def register_rows(root):
    """Rows of the register table, as dicts keyed by column position.

    The table is parsed rather than imported so the register stays a document a
    person reads, not a data file that happens to render.
    """
    path = os.path.join(root, REGISTER)
    if not os.path.exists(path):
        return None
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("|") or line.startswith("|--") or "---" in line:
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 8:
                continue
            if cells[0] in ("來源", "name", "Source"):
                continue
            rows.append({
                "name": cells[0],
                "type": cells[1],
                "path": cells[2],
                "status": cells[3],
                "learnings": cells[4],
                "adopted": cells[5],
                "rejected": cells[6],
                "last_reviewed": cells[7],
            })
    return rows


def clones_on_disk(root):
    """Directories that look like a checked-out clone."""
    out = []
    for parent in CLONE_DIRS:
        base = os.path.join(root, parent)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            full = os.path.join(base, name)
            if os.path.isdir(full):
                out.append((name, "%s/%s" % (parent, name)))
    return out


def check(root):
    failures = []
    notes = []

    rows = register_rows(root)
    if rows is None:
        return ["%s is missing — every external source must be accounted for "
                "somewhere a person can read." % REGISTER], []

    def aliases(row):
        return [a.strip() for a in row["name"].replace("、", "/").split("/") if a.strip()]

    by_name = {a: r for r in rows for a in aliases(r)}
    by_norm = {normalise(a): r for r in rows for a in aliases(r)}

    # README first: it is the list a human reads, and a repository named there
    # but missing from the register is exactly the drift this check exists for.
    for repo in sorted(readme_repos(root)):
        if normalise(repo) not in by_norm:
            failures.append(
                "%s is linked from %s but has no row in the register. The list "
                "people read and the list the tooling knows about must not drift."
                % (repo, README))

    sources = manifest_sources(root)
    for source in sources:
        if source["name"] not in by_name:
            failures.append(
                "%s is declared in %s but has no row in the register. A source "
                "nobody has written a line about is a source nobody will read."
                % (source["name"], MANIFEST))

    declared_paths = {s.get("path") for s in sources if s.get("path")}
    declared_names = {s["name"] for s in sources}
    # A clone counts as declared if the manifest lists it OR the register has a
    # row for it. Some checkouts are not this project's sources at all — someone
    # else's repository parked in the same folder — and the honest place to say
    # so is the register, not the manifest of integrated sources.
    for name, path in clones_on_disk(root):
        if path in declared_paths or name in declared_names or name in by_name:
            continue
        failures.append(
            "%s is checked out at %s but is declared nowhere — neither %s nor "
            "the register. Undeclared clones are how 11 GB accumulates without "
            "anyone deciding to keep it." % (name, path, MANIFEST))

    for row in rows:
        doc = row["learnings"]
        if doc in ("—", "-", "", "n/a"):
            continue
        for candidate in re.findall(r"[\w./-]+\.md|[\w./-]+/", doc):
            full = os.path.join(root, candidate.replace("/", os.sep))
            if not os.path.exists(full.rstrip(os.sep)):
                failures.append(
                    "%s points at %s, which does not exist."
                    % (row["name"], candidate))

    unreviewed = [r["name"] for r in rows if UNREVIEWED in r["status"]]
    reviewed = [r["name"] for r in rows if REVIEWED in r["status"]]
    notes.append("%d sources registered: %d reviewed, %d unreviewed"
                 % (len(rows), len(reviewed), len(unreviewed)))
    if unreviewed:
        notes.append("unreviewed (未審視): " + ", ".join(unreviewed))

    return failures, notes


def main():
    root = os.getcwd() if os.path.exists(os.path.join(os.getcwd(), MANIFEST)) else ROOT
    failures, notes = check(root)
    for note in notes:
        print(note)
    for failure in failures:
        print("[FAIL] " + failure)
    print("Prior-art register check complete: %d failure(s) found." % len(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
