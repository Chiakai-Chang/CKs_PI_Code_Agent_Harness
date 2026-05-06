#!/usr/bin/env python3
#
# CK's Pi Code Agent Harness – Uninstall Helper
#
# Usage:
#   python scripts/uninstall.py
#
import os
import sys
import shutil
from glob import glob

AGENT_DIR = os.path.join(os.path.expanduser("~"), ".pi", "agent")


def main():
    print("=" * 60)
    print(" CK's Pi Code Agent Harness - Uninstall")
    print("=" * 60)
    print()
    print("This will:")
    print("  - Remove skills, rules, extensions installed by this harness")
    print("  - Optionally remove Pi (AI coding assistant) itself")
    print()
    print("This will NOT:")
    print("  - Delete your projects")
    print("  - Delete your personal files")
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

    # Remove harness-installed directories
    if os.path.isdir(AGENT_DIR):
        for d in ["skills", "rules", "extensions"]:
            path = os.path.join(AGENT_DIR, d)
            if os.path.isdir(path):
                shutil.rmtree(path)
                print(f"Removed: {path}")

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
