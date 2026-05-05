#!/usr/bin/env python3
#
# CK's Pi Code Agent Harness – Restore Configuration (Python, cross-platform)
#
# Usage:
#   python scripts/restore.py
#
import sys
import os
import shutil
from datetime import datetime

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PI_DIR = os.path.join(os.path.expanduser("~"), ".pi")
AGENT_DIR = os.path.join(PI_DIR, "agent")
TIMESTAMP = datetime.now().strftime("%Y%m%dT%H%M%S")

def log(msg):
    print(f"[RESTORE] {msg}")

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def backup_agent():
    if not os.path.isdir(AGENT_DIR):
        return
    backup_dir = f"{AGENT_DIR}.backup.{TIMESTAMP}"
    log(f"Backing up existing agent config to: {backup_dir}")
    shutil.copytree(AGENT_DIR, backup_dir, dirs_exist_ok=True)

def confirm():
    if not sys.stdin.isatty():
        return True
    print()
    log("This will overwrite:")
    log("  - settings.json")
    log("  - config.json")
    log("  - skills/*")
    log("  - rules/*")
    log("  - extensions/*")
    log("  - git/.gitignore")
    log(f"A backup has been saved to: {AGENT_DIR}.backup.{TIMESTAMP}")
    print()
    ans = input("[RESTORE] Continue? (y/N): ").strip().lower()
    return ans in ("y", "yes")

def main():
    log("CK's Pi Code Agent Harness – Restore Configuration (Python)")
    log(f"Repo root: {REPO_ROOT}")
    log(f"Agent dir: {AGENT_DIR}")
    print()

    ensure_dir(AGENT_DIR)
    ensure_dir(os.path.join(AGENT_DIR, "skills"))
    ensure_dir(os.path.join(AGENT_DIR, "rules"))
    ensure_dir(os.path.join(AGENT_DIR, "extensions"))
    ensure_dir(os.path.join(AGENT_DIR, "git"))

    backup_agent()

    if not confirm():
        log("Aborted by user.")
        sys.exit(0)

    # Config
    log("Restoring config...")
    shutil.copy2(os.path.join(REPO_ROOT, "pi-config", "settings.json"),
                 os.path.join(AGENT_DIR, "settings.json"))
    shutil.copy2(os.path.join(REPO_ROOT, "pi-config", "config.json"),
                 os.path.join(AGENT_DIR, "config.json"))
    shutil.copy2(os.path.join(REPO_ROOT, "pi-config", "git", ".gitignore"),
                 os.path.join(AGENT_DIR, "git", ".gitignore"))

    # Normalize TODO_NEW_MACHINE in config.json
    log("Fixing paths in config.json...")
    cfg_path = os.path.join(AGENT_DIR, "config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            content = f.read()
        if "TODO_NEW_MACHINE" in content:
            home = os.path.expanduser("~").replace("\\", "/")
            content = content.replace("TODO_NEW_MACHINE", home)
            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write(content)

    # Skills
    log("Restoring skills...")
    skills_src = os.path.join(REPO_ROOT, "pi-skills")
    skills_dst = os.path.join(AGENT_DIR, "skills")
    if os.path.isdir(skills_src):
        for item in os.listdir(skills_dst):
            src = os.path.join(skills_dst, item)
            if os.path.isdir(src):
                shutil.rmtree(src)
            else:
                os.remove(src)
        for item in os.listdir(skills_src):
            src = os.path.join(skills_src, item)
            dst = os.path.join(skills_dst, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

    # Rules
    log("Restoring rules...")
    rules_src = os.path.join(REPO_ROOT, "pi-rules")
    rules_dst = os.path.join(AGENT_DIR, "rules")
    if os.path.isdir(rules_src):
        for item in os.listdir(rules_dst):
            src = os.path.join(rules_dst, item)
            if os.path.isdir(src):
                shutil.rmtree(src)
            else:
                os.remove(src)
        for item in os.listdir(rules_src):
            src = os.path.join(rules_src, item)
            dst = os.path.join(rules_dst, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

    # Extensions
    log("Restoring extensions...")
    ext_src = os.path.join(REPO_ROOT, "pi-extensions")
    ext_dst = os.path.join(AGENT_DIR, "extensions")
    if os.path.isdir(ext_src):
        for item in os.listdir(ext_dst):
            src = os.path.join(ext_dst, item)
            if os.path.isdir(src):
                shutil.rmtree(src)
            else:
                os.remove(src)
        for item in os.listdir(ext_src):
            src = os.path.join(ext_src, item)
            dst = os.path.join(ext_dst, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

    print()
    log("✅ Restore complete.")
    print()
    log("📌 Next steps:")
    log("  1) Ensure Pi is installed:")
    log("     - npm install -g @mariozechner/pi-coding-agent")
    log("  2) Update Pi to latest:")
    log("     - pi update")
    log("  3) Open Pi and confirm:")
    log("     - Skills loaded without conflicts")
    log("     - Extensions loaded")
    print()
    log("📌 If you use external paths (e.g., everything-claude-code),")
    log("   edit ~/.pi/agent/config.json and adjust them for your machine.")
    print()
    log("If you encounter issues, copy the output above when asking for help.")

if __name__ == "__main__":
    main()
