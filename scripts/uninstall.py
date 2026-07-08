#!/usr/bin/env python3
#
# CK's Pi Code Agent Harness – Uninstall Helper
#
# Usage:
#   python scripts/uninstall.py
#
import os
import sys
import json
import shutil
from glob import glob

# Console output contains non-ASCII status marks; legacy Windows codepages
# (e.g. cp950) crash on them when the script is run directly.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AGENT_DIR = os.path.join(os.path.expanduser("~"), ".pi", "agent")

# Must mirror the lists in scripts/restore.py: uninstall removes exactly what
# the harness manages and leaves the user's own skills/extensions alone.
MANAGED_SKILLS = ["hello-reflect", "planning-with-files", "camofox",
                  "camofox-stealth", "cua-commander", "nothing-design", "bridges"]
MANAGED_BRIDGES = ["ecc-hooks-bridge", "planning-with-files-bridge",
                   "case-bridge", "taste-bridge", "mece-autopilot-bridge"]

# Note: the stealth-recon backend stores logged-in browser profiles and cookies
# under ~/.camofox/ (session secrets). This is user data outside the harness —
# it is intentionally NOT removed here; delete it manually if desired.


def remove_path(path):
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
        print(f"Removed: {path}")
    elif os.path.exists(path):
        os.remove(path)
        print(f"Removed: {path}")


def clean_settings():
    """Strip harness-registered entries from settings.json, keep user entries."""
    settings_path = os.path.join(AGENT_DIR, "settings.json")
    if not os.path.exists(settings_path):
        return
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except Exception as e:
        print(f"Warning: could not read settings.json: {e}")
        return

    repo_prefix = REPO_ROOT.replace("\\", "/").lower()
    for key in ("skills", "extensions", "prompts"):
        entries = settings.get(key)
        if isinstance(entries, list):
            settings[key] = [
                p for p in entries
                if not p.replace("\\", "/").lower().startswith(repo_prefix)
            ]
    env = settings.get("env")
    if isinstance(env, dict):
        env.pop("PI_HARNESS_ROOT", None)

    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("Cleaned harness entries from settings.json")


def main():
    print("=" * 60)
    print(" CK's Pi Code Agent Harness - Uninstall")
    print("=" * 60)
    print()
    print("This will:")
    print("  - Remove skills, rules, extensions installed by this harness")
    print("  - Remove harness entries from settings.json")
    print("  - Optionally remove Pi (AI coding assistant) itself")
    print()
    print("This will NOT:")
    print("  - Delete your projects")
    print("  - Delete your personal files")
    print("  - Delete skills or extensions you installed yourself")
    print()

    ans = input("Continue? (y/N): ").strip().lower()
    if ans not in ("y", "yes"):
        print("Uninstall cancelled.")
        sys.exit(0)

    # Restore from latest backup if exists
    backups = sorted(glob(os.path.join(os.path.expanduser("~"), ".pi", "agent.backup.*")))
    if backups:
        latest = backups[-1]
        print(f"\nFound previous backup: {latest}")
        ans = input("Restore from backup? (y/N): ").strip().lower()
        if ans in ("y", "yes"):
            if os.path.isdir(AGENT_DIR):
                shutil.rmtree(AGENT_DIR)
            shutil.copytree(latest, AGENT_DIR)
            print("✅ Restored from backup.")
            print("Uninstall complete.")
            return

    # Remove only harness-managed items, preserving the user's own assets
    if os.path.isdir(AGENT_DIR):
        for name in MANAGED_SKILLS:
            remove_path(os.path.join(AGENT_DIR, "skills", name))
        for name in MANAGED_BRIDGES:
            remove_path(os.path.join(AGENT_DIR, "extensions", name))
        # rules/ and the global AGENTS.md are fully harness-managed (restore.py
        # clears and rewrites them wholesale)
        remove_path(os.path.join(AGENT_DIR, "rules"))
        remove_path(os.path.join(AGENT_DIR, "AGENTS.md"))
        clean_settings()

    # Ask to remove Pi itself
    print()
    ans = input("Remove Pi (pi command)? (y/N): ").strip().lower()
    if ans in ("y", "yes"):
        print("Run the following command to uninstall Pi:")
        print("  npm uninstall -g @mariozechner/pi-coding-agent")
    else:
        print("Pi kept.")

    print()
    print("✅ Uninstall complete.")


if __name__ == "__main__":
    main()
