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
import sys
from pathlib import Path


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
