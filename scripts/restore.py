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
import argparse
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
    log("  - skills/* (core + optionally design/heavy skills)")
    log("  - rules/*")
    log("  - extensions/*")
    log("  - git/.gitignore")
    log(f"A backup has been saved to: {AGENT_DIR}.backup.{TIMESTAMP}")
    print()
    ans = input("[RESTORE] Continue? (y/N): ").strip().lower()
    return ans in ("y", "yes")

def clear_dir(path):
    """
    Safely clear a directory's contents, handling symlinks, junctions, and read-only files.
    """
    if not os.path.lexists(path):
        return
    
    # If the path itself is a link/junction, just remove it
    if os.path.islink(path) or not os.path.isdir(path):
        try: os.remove(path)
        except: pass
        os.makedirs(path, exist_ok=True)
        return

    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        try:
            if os.path.islink(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                # On Windows, junctions are isdir=True but rmtree fails
                try:
                    shutil.rmtree(item_path)
                except OSError:
                    # Fallback for junctions
                    try: os.remove(item_path)
                    except: os.rmdir(item_path)
            else:
                os.remove(item_path)
        except Exception as e:
            log(f"Warning: Failed to clear {item}: {e}")

def copy_dir_contents(src, dst):
    ensure_dir(dst)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)

def load_json(path):
    if not os.path.exists(path):
        # Fallback to .example
        example = path + ".example"
        if os.path.exists(example):
            path = example
        else:
            return {}
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            import json
            return json.load(f)
    except:
        return {}

def save_json(path, data):
    ensure_dir(os.path.dirname(path) or ".")
    import json
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

def main():
    parser = argparse.ArgumentParser(description="CK's Pi Code Agent Harness - Restore")
    parser.add_argument("--auto", action="store_true", help="Skip confirmation")
    args = parser.parse_args()

    # Check environment variable as a robust fallback for --auto
    is_auto = args.auto or (os.environ.get("PI_AUTO_RESTORE") == "1")

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

    if not is_auto and not confirm():
        log("Aborted by user.")
        sys.exit(0)

    # Config
    log("Restoring config (settings, models, git)...")
    
    # 1. Patch and sync settings.json
    settings_src = os.path.join(REPO_ROOT, "pi-config", "settings.json")
    if os.path.exists(settings_src) or os.path.exists(settings_src + ".example"):
        settings = load_json(settings_src)
        if "env" not in settings: settings["env"] = {}
        settings["env"]["PI_HARNESS_ROOT"] = REPO_ROOT.replace("\\", "/")
        save_json(os.path.join(AGENT_DIR, "settings.json"), settings)
    
    # 2. Sync models.json (CRITICAL)
    models_src = os.path.join(REPO_ROOT, "pi-config", "models.json")
    if os.path.exists(models_src) or os.path.exists(models_src + ".example"):
        models_data = load_json(models_src)
        if models_data:
            save_json(os.path.join(AGENT_DIR, "models.json"), models_data)
            log("  - models.json synced")

    # 3. Sync other base configs
    config_src = os.path.join(REPO_ROOT, "pi-config", "config.json")
    if os.path.exists(config_src):
        shutil.copy2(config_src, os.path.join(AGENT_DIR, "config.json"))
    
    gitignore_src = os.path.join(REPO_ROOT, "pi-config", "git", ".gitignore")
    if os.path.exists(gitignore_src):
        shutil.copy2(gitignore_src, os.path.join(AGENT_DIR, "git", ".gitignore"))

    cfg_path = os.path.join(AGENT_DIR, "config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Resolve real paths for Superpowers
        sp_root = os.path.join(REPO_ROOT, "external", "superpowers", "skills").replace("\\", "/")
        sp_skills = {
            "using-superpowers": os.path.join(sp_root, "using-superpowers"),
            "brainstorming": os.path.join(sp_root, "brainstorming"),
            "writing-plans": os.path.join(sp_root, "writing-plans"),
            "test-driven-development": os.path.join(sp_root, "test-driven-development"),
            "systematic-debugging": os.path.join(sp_root, "systematic-debugging"),
            "subagent-driven-development": os.path.join(sp_root, "subagent-driven-development"),
            "executing-plans": os.path.join(sp_root, "executing-plans"),
            "verification-before-completion": os.path.join(sp_root, "verification-before-completion"),
            "finishing-a-development-branch": os.path.join(sp_root, "finishing-a-development-branch"),
            "receiving-code-review": os.path.join(sp_root, "receiving-code-review"),
            "requesting-code-review": os.path.join(sp_root, "requesting-code-review"),
            "using-git-worktrees": os.path.join(sp_root, "using-git-worktrees"),
            "writing-skills": os.path.join(sp_root, "writing-skills"),
        }
        
        # Resolve real paths for ECC and local skills
        ecc_agents = os.path.join(REPO_ROOT, "external", "everything-claude-code", "agents").replace("\\", "/")
        ecc_skills = os.path.join(REPO_ROOT, "external", "everything-claude-code", "skills").replace("\\", "/")
        anthropic_mcp = os.path.join(REPO_ROOT, "external", "anthropics-skills", "skills", "mcp-builder").replace("\\", "/")
        anthropic_frontend = os.path.join(REPO_ROOT, "external", "anthropics-skills", "skills", "frontend-design").replace("\\", "/")
        anthropic_testing = os.path.join(REPO_ROOT, "external", "anthropics-skills", "skills", "webapp-testing").replace("\\", "/")
        anthropic_pdf = os.path.join(REPO_ROOT, "external", "anthropics-skills", "skills", "pdf").replace("\\", "/")
        anthropic_docx = os.path.join(REPO_ROOT, "external", "anthropics-skills", "skills", "docx").replace("\\", "/")
        anthropic_creator = os.path.join(REPO_ROOT, "external", "anthropics-skills", "skills", "skill-creator").replace("\\", "/")
        karpathy_skills = os.path.join(REPO_ROOT, "external", "karpathy-skills", "skills", "karpathy-guidelines").replace("\\", "/")
        upstream_planning = os.path.join(REPO_ROOT, "external", "planning-with-files").replace("\\", "/")
        upstream_wiki = os.path.join(REPO_ROOT, "external", "llm-wiki-plugin", "skills", "llm-wiki").replace("\\", "/")
        
        # Resolve real paths for UI/UX Pro Max
        ui_root = os.path.join(REPO_ROOT, "external", "ui-ux-pro-max-skill", ".claude", "skills").replace("\\", "/")
        ui_skills = {
            "ui-ux-pro-max": os.path.join(ui_root, "ui-ux-pro-max"),
            "ui-styling": os.path.join(ui_root, "ui-styling"),
            "design": os.path.join(ui_root, "design"),
            "design-system": os.path.join(ui_root, "design-system"),
            "brand": os.path.join(ui_root, "brand"),
            "slides": os.path.join(ui_root, "slides"),
            "banner-design": os.path.join(ui_root, "banner-design"),
        }
        
        understand_agents = os.path.join(AGENT_DIR, "skills", "understand", "agents").replace("\\", "/")
        browser_agents = os.path.join(AGENT_DIR, "skills", "dev-browser", "agents").replace("\\", "/")
        caveman_skill = os.path.join(AGENT_DIR, "skills", "caveman").replace("\\", "/")
        
        # More precise replacements
        for name, path in sp_skills.items():
            placeholder = f"TODO_NEW_MACHINE:/path/to/external/superpowers/skills/{name}"
            content = content.replace(placeholder, path)
            
        for name, path in ui_skills.items():
            placeholder = f"TODO_NEW_MACHINE:/path/to/external/ui-ux-pro-max-skill/.claude/skills/{name}"
            content = content.replace(placeholder, path)

        content = content.replace("TODO_NEW_MACHINE:/path/to/external/karpathy-skills/skills/karpathy-guidelines", karpathy_skills)

        content = content.replace("TODO_NEW_MACHINE:/path/to/everything-claude-code/agents", ecc_agents)
        content = content.replace("TODO_NEW_MACHINE:/path/to/everything-claude-code/skills", ecc_skills)
        content = content.replace("TODO_NEW_MACHINE:/path/to/external/anthropics-skills/skills/mcp-builder", anthropic_mcp)
        content = content.replace("TODO_NEW_MACHINE:/path/to/external/anthropics-skills/skills/frontend-design", anthropic_frontend)
        content = content.replace("TODO_NEW_MACHINE:/path/to/external/anthropics-skills/skills/webapp-testing", anthropic_testing)
        content = content.replace("TODO_NEW_MACHINE:/path/to/external/anthropics-skills/skills/pdf", anthropic_pdf)
        content = content.replace("TODO_NEW_MACHINE:/path/to/external/anthropics-skills/skills/docx", anthropic_docx)
        content = content.replace("TODO_NEW_MACHINE:/path/to/external/anthropics-skills/skills/skill-creator", anthropic_creator)
        content = content.replace("TODO_NEW_MACHINE:/path/to/external/planning-with-files", upstream_planning)
        content = content.replace("TODO_NEW_MACHINE:/path/to/external/llm-wiki-plugin/skills/llm-wiki", upstream_wiki)
        content = content.replace("TODO_NEW_MACHINE:/path/to/pi/agent/skills/understand/agents", understand_agents)
        content = content.replace("TODO_NEW_MACHINE:/path/to/pi/agent/skills/dev-browser/agents", browser_agents)
        content = content.replace("TODO_NEW_MACHINE:/path/to/pi/agent/skills/caveman", caveman_skill)
        
        # Fallback for any other leftovers
        home = os.path.expanduser("~").replace("\\", "/")
        content = content.replace("TODO_NEW_MACHINE", home)
        
        with open(cfg_path, "w", encoding="utf-8") as f:
            f.write(content)

    # Core skills (always)
    log("Restoring core skills...")
    core_src = os.path.join(REPO_ROOT, "pi-skills", "core")
    skills_dst = os.path.join(AGENT_DIR, "skills")
    if os.path.isdir(core_src):
        clear_dir(skills_dst)
        copy_dir_contents(core_src, skills_dst)
    else:
        log("Core skills directory not found, skipping.")

    # Optional skills (design / heavy) – prompt
    optional_src = os.path.join(REPO_ROOT, "pi-skills", "optional")
    restore_optional = True

    if os.path.isdir(optional_src) and sys.stdin.isatty():
        print()
        log("This repo includes optional design/creative skills (heavier).")
        log("Examples: design, ui-ux-pro-max, ui-styling, slides, brand, etc.")
        ans = input("[RESTORE] Restore optional skills? (Y/n): ").strip().lower()
        if ans in ("n", "no"):
            restore_optional = False

    if restore_optional and os.path.isdir(optional_src):
        log("Restoring optional skills...")
        copy_dir_contents(optional_src, skills_dst)
    else:
        log("Optional skills skipped.")

    # Rules
    log("Restoring rules...")
    rules_src = os.path.join(REPO_ROOT, "pi-rules")
    rules_dst = os.path.join(AGENT_DIR, "rules")
    if os.path.isdir(rules_src):
        clear_dir(rules_dst)
        copy_dir_contents(rules_src, rules_dst)

    # Extensions
    log("Restoring extensions...")
    ext_src = os.path.join(REPO_ROOT, "pi-extensions")
    ext_dst = os.path.join(AGENT_DIR, "extensions")
    if os.path.isdir(ext_src):
        clear_dir(ext_dst)
        copy_dir_contents(ext_src, ext_dst)
        
        # Patch bridges with absolute path for global robustness
        for bridge in ["ecc-hooks-bridge", "planning-with-files-bridge"]:
            pkg_path = os.path.join(ext_dst, bridge, "package.json")
            if os.path.exists(pkg_path):
                pkg = load_json(pkg_path)
                if "pi-harness" not in pkg: pkg["pi-harness"] = {}
                pkg["pi-harness"]["root"] = REPO_ROOT.replace("\\", "/")
                save_json(pkg_path, pkg)
                log(f"  - {bridge} patched with absolute path")

    # models.json (v0.73+ format)
    models_src = os.path.join(REPO_ROOT, "pi-config", "models.json")
    models_dst = os.path.join(AGENT_DIR, "models.json")
    if os.path.exists(models_src):
        log("Restoring models.json to agent dir...")
        shutil.copy2(models_src, models_dst)

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
