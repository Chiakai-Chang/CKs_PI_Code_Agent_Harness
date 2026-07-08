#!/usr/bin/env python3
#
# CK's Pi Code Agent Harness – Uninstall Helper
#
# Usage:
#   python scripts/uninstall.py            # remove harness-managed items only
#   python scripts/uninstall.py --purge    # full clean-slate (per-item confirm)
#
import os
import sys
import json
import shutil
import argparse
import subprocess
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
# under ~/.camofox/ (session secrets). The default uninstall leaves it in place;
# it is removed only under --purge, and only after an explicit y confirmation.


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


def ask(prompt, default="n"):
    """Interactive y/N that degrades to default (no) in non-tty runs — never deletes unattended."""
    if not sys.stdin.isatty():
        print(f"{prompt}{default} (auto)")
        return default
    try:
        return input(prompt).strip().lower()
    except EOFError:
        return default


def _purge():
    """Full clean-slate: each destructive step confirmed, default No."""
    print()
    print("[--purge] 完整刪除 — 逐項確認 (預設 N):")
    home = os.path.expanduser("~")
    if ask("刪除 ~/.camofox（登入 profile/cookies + Camoufox 快取）? [y/N]: ") in ("y", "yes"):
        remove_path(os.path.join(home, ".camofox"))
    if ask("刪除 restore 備份 ~/.pi/agent.backup.*? [y/N]: ") in ("y", "yes"):
        for b in glob(os.path.join(home, ".pi", "agent.backup.*")):
            remove_path(b)
    if ask("執行 npm uninstall -g @earendil-works/pi-coding-agent? [y/N]: ") in ("y", "yes"):
        try:
            r = subprocess.run("npm uninstall -g @earendil-works/pi-coding-agent", shell=True)
            if r.returncode != 0:
                print("  npm uninstall 回傳非零（npm 可能未安裝）；可手動執行: npm uninstall -g @earendil-works/pi-coding-agent")
        except Exception as e:
            print(f"  npm uninstall 失敗: {e}；可手動執行。")
    else:
        print("  可手動執行: npm uninstall -g @earendil-works/pi-coding-agent")
    print()
    remaining = glob(os.path.join(home, ".pi", "agent.backup.*"))
    if remaining:
        print(f"（保留了 {len(remaining)} 份 ~/.pi/agent 備份；不需要可手動刪除。）")
    print(f"最後一步（程式無法自刪所在目錄）：請手動刪除 repo 資料夾：{REPO_ROOT}")


def main():
    parser = argparse.ArgumentParser(description="CK's Pi Code Agent Harness - Uninstall")
    parser.add_argument("--purge", action="store_true",
                        help="Also remove ~/.camofox, restore backups, and optionally Pi itself")
    args = parser.parse_args()

    print("=" * 60)
    print(" CK's Pi Code Agent Harness - Uninstall" + (" (--purge)" if args.purge else ""))
    print("=" * 60)
    print()
    print("This will:")
    print("  - Remove skills, rules, extensions installed by this harness")
    print("  - Remove harness entries from settings.json")
    if args.purge:
        print("  - [--purge] Also offer to remove ~/.camofox, backups, and Pi")
    print()
    print("This will NOT:")
    print("  - Delete your projects")
    print("  - Delete your personal files")
    print("  - Delete skills or extensions you installed yourself")
    print()

    if ask("Continue? (y/N): ") not in ("y", "yes"):
        print("Uninstall cancelled.")
        sys.exit(0)

    # Restore from latest backup if exists (skipped under --purge: purge is a
    # clean-slate path, not a restore).
    backups = sorted(glob(os.path.join(os.path.expanduser("~"), ".pi", "agent.backup.*")))
    if backups and not args.purge:
        latest = backups[-1]
        print(f"\nFound previous backup: {latest}")
        if ask("Restore from backup? (y/N): ") in ("y", "yes"):
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

    if args.purge:
        _purge()
    else:
        print()
        if ask("Remove Pi (pi command)? (y/N): ") in ("y", "yes"):
            print("Run the following command to uninstall Pi:")
            print("  npm uninstall -g @earendil-works/pi-coding-agent")
        else:
            print("Pi kept.")

    print()
    print("✅ Uninstall complete.")


if __name__ == "__main__":
    main()
