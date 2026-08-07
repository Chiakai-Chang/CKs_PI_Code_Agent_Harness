#!/usr/bin/env python3
"""Verify bridge health: check that every registered bridge has a valid entry point.

Usage:
    python scripts/verify-bridges.py [--root ROOT]

Checks performed (stdlib only):
    1. bridge-manifest.json exists and parses as valid JSON with version + bridges array.
    2. Each bridge entry has required fields (name, entry, version, description).
    3. Each bridge entry path exists as a file relative to the repo root.
    4. package.json exists in each bridge directory (co-located with the entry point).
    5. Cross-check: every extension registered in package.json#pi.extensions has a manifest entry,
       and vice versa (no orphan registrations).

Exit code 0 = all checks pass; 1 = one or more failures found.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


_LOCAL_IMPORT_RE = re.compile(r"""(?:from|import)\s*\(?\s*["'](\.\.?/[^"']+)["']""")

# Where restore.py copies the bridges, and the one field it rewrites on arrival.
DEFAULT_INSTALL_DIR = os.path.join(os.path.expanduser("~"), ".pi", "agent", "extensions")
_INJECTED = ("pi-harness", "root")
_INJECTED_SENTINEL = "<injected-by-restore>"


def _files_under(directory: Path) -> set:
    return {
        str(p.relative_to(directory)).replace(os.sep, "/")
        for p in directory.rglob("*")
        if p.is_file()
    }


def _package_json_differs(repo_file: Path, installed_file: Path) -> bool:
    """package.json comparison with the injected root normalised away.

    `restore.py:1279` writes this machine's absolute path into
    `pi-harness.root` on every installed copy, so all thirteen differ by
    design. Exempting the whole filename is the cheaper thing to write and
    would park every other package.json defect behind the exemption; a
    threshold defines the shape of the evasion. Only the field moves.

    Unparseable JSON counts as differing rather than raising: an installed
    package.json that Pi cannot read is a real problem, and the caller's job
    is to report it, not to crash on it.
    """
    def normalised(path: Path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
        section = data.get(_INJECTED[0])
        if isinstance(section, dict):
            section.pop(_INJECTED[1], None)
            # restore.py creates the section when the repo file lacks one, so an
            # empty leftover must read as absent or every such bridge is drift.
            if not section:
                data.pop(_INJECTED[0], None)
        return data

    a, b = normalised(repo_file), normalised(installed_file)
    if a is None or b is None:
        return True
    return a != b


def installed_drift(repo_ext_dir, installed_ext_dir, bridge_dirs):
    """What Pi would load, minus what the repo says — or None if nothing is installed.

    Pi auto-discovers `~/.pi/agent/extensions/*/index.ts` by directory
    (`restore.py:1100-1109`, which also records that listing the repo paths in
    settings.json made every bridge load twice until `registerTool()` collided).
    So the copies are the running code and the repo is only its source.

    Measured 2026-08-08: `harness-root.ts` was written, wired, tested, committed
    and pushed while the installed `yes-hooks-bridge` had no such file — restore
    was never run, and Pi loaded the pre-fix version all day. 910 unit tests, the
    bridge verifier and two other checks all passed on that state.

    Returns a sorted list of `(kind, "<bridge>/<relative path>")` where kind is
    "missing" (in the repo, never installed — the shape of the 2026-08-08
    defect, and invisible to any check that compares only files present in
    both), "changed" (edited without a restore), or "extra" (renamed in the
    repo, old module still installed; restore deletes the directory first, so
    this means no restore has run since).

    Returns None — not an empty list — when `installed_ext_dir` does not exist.
    CI checks out a fresh repo with no `~/.pi`, and an empty list there would
    read as a clean bill of health on every automated run.
    """
    installed_root = Path(installed_ext_dir)
    if not installed_root.is_dir():
        return None

    repo_root = Path(repo_ext_dir)
    drift = []
    for bridge in bridge_dirs:
        repo_bridge = repo_root / bridge
        if not repo_bridge.is_dir():
            continue  # the entry-path check above owns a bridge missing from the repo
        installed_bridge = installed_root / bridge
        installed_files = _files_under(installed_bridge) if installed_bridge.is_dir() else set()
        repo_files = _files_under(repo_bridge)

        for rel in sorted(repo_files - installed_files):
            drift.append(("missing", f"{bridge}/{rel}"))
        for rel in sorted(installed_files - repo_files):
            drift.append(("extra", f"{bridge}/{rel}"))
        for rel in sorted(repo_files & installed_files):
            a, b = repo_bridge / rel, installed_bridge / rel
            if rel.endswith("package.json"):
                if _package_json_differs(a, b):
                    drift.append(("changed", f"{bridge}/{rel}"))
            elif a.read_bytes() != b.read_bytes():
                drift.append(("changed", f"{bridge}/{rel}"))
    return sorted(drift)


def missing_local_imports(entry_path) -> list:
    """Relative modules an entry file imports that are not on disk beside it.

    A bridge whose entry point exists is not a bridge that loads: six of the
    twelve import sibling modules, and Pi fails the extension at session start if
    one of them did not come along. Nothing checked for that.

    Both specifier styles in this repo are accepted. `./x.ts` names the file
    directly; `./x.js` is used by deep-research-bridge and stealth-web-bridge for
    files that are `.ts` on disk, so either extension satisfies it.
    """
    entry = Path(entry_path)
    try:
        body = entry.read_text(encoding="utf-8")
    except OSError:
        # The entry-exists check owns that failure; reporting it twice buries it.
        return []

    missing = []
    for spec in _LOCAL_IMPORT_RE.findall(body):
        target = (entry.parent / spec).resolve()
        candidates = [target]
        if target.suffix == ".js":
            candidates.append(target.with_suffix(".ts"))
        elif target.suffix == ".ts":
            candidates.append(target.with_suffix(".js"))
        if not any(c.is_file() for c in candidates):
            missing.append(spec)
    return missing


def find_repo_root(start: str | None) -> Path:
    root = Path(start).resolve() if start else Path.cwd().resolve()
    for candidate in [root, *root.parents]:
        if (candidate / ".git").exists():
            return candidate
    print(f"ERROR: could not find repo root starting from {root}", file=sys.stderr)
    sys.exit(2)


def load_json(path: Path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"FAIL: {path} not found")
        return None
    except json.JSONDecodeError as exc:
        print(f"FAIL: {path} is not valid JSON: {exc}")
        return None


def verify_bridges(root: Path) -> int:
    errors = 0

    # --- Load manifest ---
    manifest_path = root / "pi-extensions" / "bridge-manifest.json"
    manifest = load_json(manifest_path)
    if manifest is None:
        return 1

    if not isinstance(manifest, dict):
        print("FAIL: bridge-manifest.json top level must be an object")
        return 1

    if manifest.get("version") != 1:
        print(f"FAIL: unsupported bridge-manifest version {manifest.get('version')!r}; expected 1")
        errors += 1

    bridges = manifest.get("bridges")
    if not isinstance(bridges, list):
        print("FAIL: bridge-manifest.json must contain a 'bridges' array")
        return 1

    required_fields = {"name", "entry", "version", "description"}
    seen_names: set[str] = set()

    for i, bridge in enumerate(bridges):
        if not isinstance(bridge, dict):
            print(f"FAIL: bridges[{i}] must be an object")
            errors += 1
            continue

        missing = required_fields - bridge.keys()
        if missing:
            print(f"FAIL: bridges[{i}] missing fields: {sorted(missing)}")
            errors += 1

        name = bridge.get("name", f"<unnamed [{i}]>")
        entry = bridge.get("entry")
        if name in seen_names:
            print(f"FAIL: duplicate bridge name '{name}' at bridges[{i}]")
            errors += 1
        seen_names.add(name)

        if not entry or not isinstance(entry, str):
            continue

        entry_path = root / entry
        if not entry_path.is_file():
            print(f"FAIL: bridge '{name}' entry path does not exist: {entry_path}")
            errors += 1
        else:
            pkg = entry_path.parent / "package.json"
            if not pkg.is_file():
                print(f"WARN: bridge '{name}' directory lacks package.json: {pkg}")
            gone = missing_local_imports(entry_path)
            if gone:
                print(f"FAIL: bridge '{name}' entry imports modules that are not "
                      f"beside it: {', '.join(gone)}")
                errors += 1

    # --- Cross-check against package.json registrations ---
    # package.json#pi.extensions is the harness shipping registry;
    # per-machine Pi runtime registration lives in pi-config/settings.json (gitignored).
    pkg_json_path = root / "package.json"
    pkg = load_json(pkg_json_path)
    shipped_extensions: list[str] = []
    if isinstance(pkg, dict):
        pi_section = pkg.get("pi")
        if isinstance(pi_section, dict):
            shipped_extensions = list(pi_section.get("extensions", []))

    manifest_entries = {b.get("entry") for b in bridges if isinstance(b, dict) and b.get("entry")}

    for reg in shipped_extensions:
        if reg not in manifest_entries:
            print(f"WARN: extension shipped in package.json but absent from bridge-manifest: '{reg}'")

    for entry in sorted(manifest_entries):
        if entry not in shipped_extensions:
            print(
                f"INFO: bridge in manifest but not shipped in package.json#pi.extensions ("
                f"may be Pi-runtime-only via settings.json): '{entry}'"
            )

    # --- Repo vs what Pi actually loads ---
    bridge_dirs = sorted({
        Path(e).parent.name for e in manifest_entries if isinstance(e, str)
    })
    install_dir = os.environ.get("PI_HARNESS_INSTALL_DIR") or DEFAULT_INSTALL_DIR
    drift = installed_drift(root / "pi-extensions", install_dir, bridge_dirs)
    if drift is None:
        print(
            f"\nSKIP: no installed bridges at {install_dir} — this run did NOT "
            f"check whether the repo matches what Pi loads. That check only has "
            f"an answer on a machine with Pi installed; run it there before "
            f"believing a bridge fix is live."
        )
    elif drift:
        print(f"\nFAIL: {len(drift)} file(s) differ between the repo and the installed "
              f"bridges Pi loads from {install_dir}.")
        for kind, rel in drift:
            print(f"  {kind:<8} {rel}")
        print("  Fix: python scripts/setup.py --mode restore")
        errors += len(drift)
    else:
        print(f"\nOK: installed bridges at {install_dir} match the repo "
              f"({len(bridge_dirs)} bridges compared).")

    # --- Summary ---
    print(f"\nBridge verification complete: {len(bridges)} bridges checked, {errors} failure(s) found.")
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description="Verify bridge entry points and registrations.")
    parser.add_argument("--root", default=None, help="Repository root directory (default: detected from .git)")
    args = parser.parse_args()

    root = find_repo_root(args.root)
    print(f"Repo root: {root}")
    sys.exit(verify_bridges(root))


if __name__ == "__main__":
    main()
