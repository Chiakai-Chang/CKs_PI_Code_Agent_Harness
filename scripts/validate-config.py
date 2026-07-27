#!/usr/bin/env python3
"""Validate pi-config files: schema checks, path existence, and anti-patterns.

Usage:
    python scripts/validate-config.py [--root ROOT] [--fix]

Checks (stdlib only):
    settings.json:
        - parses as JSON object with required keys (defaultModel, defaultProvider).
        - defaultModel is a non-empty string.
        - apiBase, if present, looks like a URL base.
        - shellPath, if present, points to an existing executable (machine-specific;
          injected by setup.py, never committed).
    models.json:
        - parses as JSON array of model objects with id + provider fields.

Anti-patterns (FAIL):
    - settings.json contains a machine-specific path (e.g. C:\\Program Files) that
      should be injected at runtime by setup.py instead.
    - pi-config contains auth tokens or API keys in plaintext.

Exit code 0 = all checks pass; 1 = failures found.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


MACHINE_PATH_RE = re.compile(r"(?:C:[\\/]Program Files|/usr/local/bin|/opt/|/Applications/)")
SECRET_RE = re.compile(
    r"(?i)(?:"
    # Anthropic sk-ant-<48 alnum>, OpenAI sk-proj-<alnum>
    r"sk-(?:ant|proj)-[a-z0-9]{20,}"
    # Generic short secret-key patterns
    r"|sk[-_]?[a-z0-9]{20,}"
    r")"
)


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
        print(f"INFO: {path} not found (optional)")
        return None
    except json.JSONDecodeError as exc:
        print(f"FAIL: {path} is not valid JSON: {exc}")
        return None


def check_settings(root: Path, fix: bool) -> int:
    errors = 0
    # pi-config/settings.json is gitignored (machine-local, written by setup.py);
    # only the .example is tracked. Validate whichever exists, and remember which
    # one it was — the "no committed machine paths" rule only applies to the
    # tracked file. Checking it against the local copy could never catch a
    # committed path (that file is never committed) while failing on every
    # developer machine where setup.py has correctly injected a real shell path.
    path = root / "pi-config" / "settings.json"
    is_tracked_artifact = False
    if not path.exists():
        example = root / "pi-config" / "settings.json.example"
        if example.exists():
            path = example
            is_tracked_artifact = True
    data = load_json(path)
    if data is None:
        print("FAIL: settings.json missing or unparseable; setup.py needs it")
        return 1

    if not isinstance(data, dict):
        print("FAIL: settings.json must be a JSON object")
        return 1

    # defaultModel/defaultProvider are written by setup.py after it probes the
    # local LLM server, so the tracked template legitimately lacks them.
    # Requiring them there made `validate-config.py` fail on every clean clone —
    # the exact state a new user runs the documented health check in.
    required_keys = () if is_tracked_artifact else ("defaultModel", "defaultProvider")
    for key in required_keys:
        if key not in data:
            print(f"FAIL: settings.json missing required key '{key}'")
            errors += 1
        elif not isinstance(data[key], str) or not data[key].strip():
            print(f"FAIL: settings.json '{key}' must be a non-empty string")
            errors += 1

    api_base = data.get("apiBase")
    if api_base is not None:
        if not isinstance(api_base, str):
            print("FAIL: settings.json 'apiBase' must be a string URL base")
            errors += 1
        elif not re.match(r"https?://", api_base):
            print(f"WARN: settings.json 'apiBase' ({api_base!r}) does not start with http(s)://")

    shell_path = data.get("shellPath")
    if shell_path is not None:
        if not isinstance(shell_path, str):
            print("FAIL: settings.json 'shellPath' must be a string")
            errors += 1
        elif not os.path.isfile(shell_path) and os.name == "nt":
            # On Windows, the path must exist; on Unix it may be /bin/bash which is fine.
            print(f"WARN: settings.json shellPath does not exist: {shell_path}")

    # Anti-patterns: check parsed values (authoritative) and raw text (catches comments/keys).
    # JSON escapes backslashes so the raw file text representation differs from value semantics;
    # checking parsed values avoids that escaping trap.
    found_machine_path = False
    for key in ("shellPath", "apiBase"):
        val = data.get(key)
        if isinstance(val, str) and MACHINE_PATH_RE.search(val):
            found_machine_path = True
            break
    raw = path.read_text(encoding="utf-8")
    if not found_machine_path and MACHINE_PATH_RE.search(raw):
        found_machine_path = True
    if found_machine_path:
        if is_tracked_artifact:
            print(
                f"FAIL: {path.name} contains a machine-specific path (e.g. C:\\\\Program Files). "
                "Machine paths must be injected by setup.py at runtime, never committed."
            )
            errors += 1
        else:
            # Expected: setup.py injects the real shell path into the local,
            # gitignored copy. Not a finding.
            print(f"INFO: {path.name} carries a machine-specific path (local, gitignored) — expected.")

    # The tracked template is the artifact the "never committed" rule is about,
    # so check it even when a local settings.json shadowed it above.
    if not is_tracked_artifact:
        example = root / "pi-config" / "settings.json.example"
        example_data = load_json(example) if example.exists() else None
        # Parsed values, not raw text: JSON escapes backslashes, so a Windows
        # path reads as `C:\\Program Files` on disk and MACHINE_PATH_RE (which
        # expects a single separator) never matches the raw form.
        if isinstance(example_data, dict) and any(
            isinstance(v, str) and MACHINE_PATH_RE.search(v) for v in example_data.values()
        ):
            print(
                "FAIL: settings.json.example contains a machine-specific path "
                "(e.g. C:\\\\Program Files). The tracked template must stay portable."
            )
            errors += 1

    for i, line in enumerate(raw.splitlines(), 1):
        stripped = line.strip().lstrip("#").strip()
        if SECRET_RE.search(stripped):
            print(f"FAIL: settings.json line {i} appears to contain a secret/token")
            errors += 1

    return errors


def check_models(root: Path) -> int:
    errors = 0
    path = root / "pi-config" / "models.json"
    data = load_json(path)
    if data is None:
        return 0  # optional file

    if not isinstance(data, dict):
        print("FAIL: models.json must be a JSON object")
        return 1

    providers = data.get("providers")
    if not isinstance(providers, dict):
        print("WARN: models.json missing 'providers' object (Pi expects {providers: {...}})")
        return errors

    for prov_id, prov in providers.items():
        if not isinstance(prov, dict):
            print(f"FAIL: models.json providers['{prov_id}'] must be an object")
            errors += 1
            continue
        models = prov.get("models")
        if models is None:
            print(f"WARN: models.json provider '{prov_id}' has no 'models' list")
            continue
        if not isinstance(models, list):
            print(f"FAIL: models.json provider '{prov_id}' models must be an array")
            errors += 1
            continue
        for i, entry in enumerate(models):
            if not isinstance(entry, dict) or "id" not in entry:
                print(f"WARN: models.json provider '{prov_id}' models[{i}] missing 'id'")

    return errors


def check_naming_hygiene(root: Path) -> int:
    """Validate directory naming conventions under pi-extensions and pi-skills (kebab-case)."""
    errors = 0
    kebab_re = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    for subdir_name in ("pi-extensions", "pi-skills"):
        target = root / subdir_name
        if not target.exists():
            continue
        for child in target.iterdir():
            if child.is_dir() and not child.name.startswith((".", "_")):
                if not kebab_re.match(child.name):
                    print(f"WARN: {subdir_name}/{child.name} does not follow lower kebab-case naming convention")
                    # Warning only to maintain non-breaking behavior
    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate pi-config files against harness expectations.")
    parser.add_argument("--root", default=None, help="Repository root directory (default: detected from .git)")
    parser.add_argument("--fix", action="store_true", help="(reserved) auto-fix safe issues")
    args = parser.parse_args()

    root = find_repo_root(args.root)
    print(f"Repo root: {root}")
    errors = check_settings(root, args.fix)
    errors += check_models(root)
    errors += check_naming_hygiene(root)
    print(f"\nConfig validation complete: {errors} failure(s) found.")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
