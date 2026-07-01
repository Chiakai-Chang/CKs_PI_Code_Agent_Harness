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

def deep_merge(target, source):
    for key, value in source.items():
        if key in target:
            if isinstance(target[key], dict) and isinstance(value, dict):
                deep_merge(target[key], value)
            elif isinstance(target[key], list) and isinstance(value, list):
                for item in value:
                    if item not in target[key]:
                        target[key].append(item)
            else:
                # target value takes precedence
                pass
        else:
            target[key] = value
    return target

def main():
    parser = argparse.ArgumentParser(description="CK's Pi Code Agent Harness - Restore")
    parser.add_argument("--auto", action="store_true", help="Skip confirmation")
    parser.add_argument("--profile", choices=["minimal", "standard", "full"], default="standard", help="Skill profile to load")
    args = parser.parse_args()

    # Check environment variable as a robust fallback for --auto
    is_auto = args.auto or (os.environ.get("PI_AUTO_RESTORE") == "1")
    profile = args.profile or os.environ.get("PI_HARNESS_PROFILE", "standard")

    log("CK's Pi Code Agent Harness – Restore Configuration (Python)")
    log(f"Repo root: {REPO_ROOT}")
    log(f"Agent dir: {AGENT_DIR}")
    log(f"Profile:   {profile}")
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
    
    # 1. Load and merge settings.json
    settings_dest = os.path.join(AGENT_DIR, "settings.json")
    settings_src = os.path.join(REPO_ROOT, "pi-config", "settings.json")
    
    settings = {}
    if os.path.exists(settings_dest):
        settings = load_json(settings_dest)
    
    default_settings = load_json(settings_src)
    settings = deep_merge(settings, default_settings)
    
    if "env" not in settings: settings["env"] = {}
    settings["env"]["PI_HARNESS_ROOT"] = REPO_ROOT.replace("\\", "/")
    
    # 2. Dynamic Submodule Paths Resolution
    ext_root = os.path.join(REPO_ROOT, "external").replace("\\", "/")
    pi_skills_root = os.path.join(REPO_ROOT, "pi-skills").replace("\\", "/")
    pi_extensions_root = os.path.join(REPO_ROOT, "pi-extensions").replace("\\", "/")

    profile_skills = []
    profile_extensions = []
    profile_prompts = []

    # Local core skills (always loaded)
    profile_skills.append(os.path.join(pi_skills_root, "core").replace("\\", "/"))
    profile_skills.append(os.path.join(pi_skills_root, "chrome-cdp").replace("\\", "/"))
    profile_skills.append(os.path.join(pi_skills_root, "dev-browser").replace("\\", "/"))

    # Minimal profile
    if profile == "minimal":
        profile_skills.append(os.path.join(ext_root, "caveman", "skills", "caveman").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "ecc-hooks-bridge").replace("\\", "/"))

    # Standard profile (Default)
    elif profile == "standard":
        # Caveman skills
        for name in ["caveman", "caveman-commit", "caveman-review", "caveman-compress", 
                     "caveman-stats", "caveman-help", "cavecrew"]:
            profile_skills.append(os.path.join(ext_root, "caveman", "skills", name).replace("\\", "/"))
        
        # Superpowers skills
        sp_root = os.path.join(ext_root, "superpowers", "skills")
        for name in ["using-superpowers", "brainstorming", "writing-plans", "test-driven-development", 
                     "systematic-debugging", "subagent-driven-development", "executing-plans", 
                     "verification-before-completion", "finishing-a-development-branch", 
                     "receiving-code-review", "requesting-code-review", "using-git-worktrees", "writing-skills"]:
            profile_skills.append(os.path.join(sp_root, name).replace("\\", "/"))
            
        profile_skills.append(os.path.join(ext_root, "karpathy-skills", "skills", "karpathy-guidelines").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "planning-with-files", ".pi", "skills", "planning-with-files").replace("\\", "/"))
        profile_prompts.append(os.path.join(ext_root, "planning-with-files", "commands").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "llm-wiki-plugin", "skills", "llm-wiki").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "prompt-master").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "ecc", "skills").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "Local-Agent-Workspace").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "taste-skill", "skills").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "darwin-skill").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "qiushi-skill", "skills").replace("\\", "/"))
        ui_root = os.path.join(ext_root, "ui-ux-pro-max-skill", ".claude", "skills")
        for name in ["ui-ux-pro-max", "ui-styling"]:
            profile_skills.append(os.path.join(ui_root, name).replace("\\", "/"))

        # Extensions
        profile_extensions.append(os.path.join(pi_extensions_root, "ecc-hooks-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "planning-with-files-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "case-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "taste-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "darwin-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "qiushi-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "pip-guardian").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "governance-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "evolution-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "aixbdd-bridge").replace("\\", "/"))

    # Full profile
    elif profile == "full":
        # Caveman skills
        for name in ["caveman", "caveman-commit", "caveman-review", "caveman-compress", 
                     "caveman-stats", "caveman-help", "cavecrew"]:
            profile_skills.append(os.path.join(ext_root, "caveman", "skills", name).replace("\\", "/"))
        
        # Superpowers skills
        sp_root = os.path.join(ext_root, "superpowers", "skills")
        for name in ["using-superpowers", "brainstorming", "writing-plans", "test-driven-development", 
                     "systematic-debugging", "subagent-driven-development", "executing-plans", 
                     "verification-before-completion", "finishing-a-development-branch", 
                     "receiving-code-review", "requesting-code-review", "using-git-worktrees", "writing-skills"]:
            profile_skills.append(os.path.join(sp_root, name).replace("\\", "/"))
            
        profile_skills.append(os.path.join(ext_root, "karpathy-skills", "skills", "karpathy-guidelines").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "planning-with-files", ".pi", "skills", "planning-with-files").replace("\\", "/"))
        profile_prompts.append(os.path.join(ext_root, "planning-with-files", "commands").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "llm-wiki-plugin", "skills", "llm-wiki").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "prompt-master").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "ecc", "skills").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "Local-Agent-Workspace").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "taste-skill", "skills").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "darwin-skill").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "qiushi-skill", "skills").replace("\\", "/"))

        # UI/UX Pro Max
        ui_root = os.path.join(ext_root, "ui-ux-pro-max-skill", ".claude", "skills")
        for name in ["ui-ux-pro-max", "ui-styling", "design", "design-system", "brand", "slides", "banner-design"]:
            profile_skills.append(os.path.join(ui_root, name).replace("\\", "/"))

        # Matt Pocock
        mp_root = os.path.join(ext_root, "mattpocock-skills", "skills")
        for name, parent in [("zoom-out", "engineering"), ("improve-codebase-architecture", "engineering"), 
                             ("diagnose", "engineering"), ("grill-with-docs", "engineering"), ("handoff", "productivity")]:
            profile_skills.append(os.path.join(mp_root, parent, name).replace("\\", "/"))

        # Addy Osmani
        addy_root = os.path.join(ext_root, "agent-skills", "skills")
        for name in ["performance-optimization", "doubt-driven-development", "api-and-interface-design", 
                     "deprecation-and-migration", "documentation-and-adrs", "browser-testing-with-devtools"]:
            profile_skills.append(os.path.join(addy_root, name).replace("\\", "/"))

        # Nuwa-Skill
        nuwa_root = os.path.join(ext_root, "nuwa-skill")
        profile_skills.append(nuwa_root.replace("\\", "/"))
        for name in ["andrej-karpathy-perspective", "elon-musk-perspective", "feynman-perspective",
                     "ilya-sutskever-perspective", "mrbeast-perspective", "munger-perspective",
                     "naval-perspective", "paul-graham-perspective", "steve-jobs-perspective",
                     "sun-yuchen-perspective", "taleb-perspective", "trump-perspective",
                     "x-mastery-mentor", "zhang-yiming-perspective", "zhangxuefeng-perspective"]:
            profile_skills.append(os.path.join(nuwa_root, "examples", name).replace("\\", "/"))

        # Single Submodule Skills
        for name in ["mcp-builder", "frontend-design", "webapp-testing", "pdf", "docx", "skill-creator"]:
            profile_skills.append(os.path.join(ext_root, "anthropics-skills", "skills", name).replace("\\", "/"))

        # Optional core skills
        profile_skills.append(os.path.join(pi_skills_root, "optional").replace("\\", "/"))

        # Open Design skills
        profile_skills.append(os.path.join(ext_root, "open-design", "skills").replace("\\", "/"))

        # Extensions
        profile_extensions.append(os.path.join(pi_extensions_root, "ecc-hooks-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "planning-with-files-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "case-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "taste-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "darwin-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "qiushi-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "pip-guardian").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "governance-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "evolution-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "aixbdd-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "omc-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "addyosmani-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "pm-skills-bridge").replace("\\", "/"))

    # 3. Filter existing settings to keep user's custom skills/extensions not managed by Harness
    existing_skills = settings.get("skills", [])
    clean_skills = [p for p in existing_skills if not p.replace("\\", "/").startswith(REPO_ROOT.replace("\\", "/"))]
    for s in profile_skills:
        if s not in clean_skills:
            clean_skills.append(s)
    settings["skills"] = clean_skills

    existing_extensions = settings.get("extensions", [])
    clean_extensions = [p for p in existing_extensions if not p.replace("\\", "/").startswith(REPO_ROOT.replace("\\", "/"))]
    for e in profile_extensions:
        if e not in clean_extensions:
            clean_extensions.append(e)
    settings["extensions"] = clean_extensions

    existing_prompts = settings.get("prompts", [])
    clean_prompts = [p for p in existing_prompts if not p.replace("\\", "/").startswith(REPO_ROOT.replace("\\", "/"))]
    for pr in profile_prompts:
        if pr not in clean_prompts:
            clean_prompts.append(pr)
    settings["prompts"] = clean_prompts

    save_json(settings_dest, settings)
    log("  - settings.json updated with submodule paths")

    # Sync models.json (CRITICAL)
    models_src = os.path.join(REPO_ROOT, "pi-config", "models.json")
    if os.path.exists(models_src):
        models_data = load_json(models_src)
        if models_data:
            save_json(os.path.join(AGENT_DIR, "models.json"), models_data)
            log("  - models.json synced")

    # Clean up deprecated config.json in ~/.pi/agent/
    cfg_path = os.path.join(AGENT_DIR, "config.json")
    if os.path.exists(cfg_path):
        try:
            os.remove(cfg_path)
            log("  - Removed deprecated config.json")
        except Exception as e:
            log(f"  - Warning: Failed to remove config.json: {e}")

    # Sync other base configs
    gitignore_src = os.path.join(REPO_ROOT, "pi-config", "git", ".gitignore")
    if os.path.exists(gitignore_src):
        shutil.copy2(gitignore_src, os.path.join(AGENT_DIR, "git", ".gitignore"))

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

    if os.path.isdir(optional_src) and sys.stdin.isatty() and profile == "full":
        print()
        log("This repo includes optional design/creative skills (heavier).")
        log("Examples: design, ui-ux-pro-max, ui-styling, slides, brand, etc.")
        ans = input("[RESTORE] Restore optional skills? (Y/n): ").strip().lower()
        if ans in ("n", "no"):
            restore_optional = False

    if restore_optional and os.path.isdir(optional_src) and profile == "full":
        log("Restoring optional skills...")
        copy_dir_contents(optional_src, skills_dst)
    else:
        log("Optional skills skipped (or not full profile).")

    # Rules
    log("Restoring rules...")
    rules_src = os.path.join(REPO_ROOT, "pi-rules")
    rules_dst = os.path.join(AGENT_DIR, "rules")
    if os.path.isdir(rules_src):
        clear_dir(rules_dst)
        copy_dir_contents(rules_src, rules_dst)
        
        # Copy global AGENTS.md natively supported by Pi
        global_agents_md = os.path.join(rules_src, "AGENTS.md")
        if os.path.exists(global_agents_md):
            shutil.copy2(global_agents_md, os.path.join(AGENT_DIR, "AGENTS.md"))
            log("  - Copied global AGENTS.md to agent dir")

    # Extensions
    log("Restoring extensions...")
    ext_src = os.path.join(REPO_ROOT, "pi-extensions")
    ext_dst = os.path.join(AGENT_DIR, "extensions")
    if os.path.isdir(ext_src):
        clear_dir(ext_dst)
        copy_dir_contents(ext_src, ext_dst)
        
        # Patch bridges with absolute path for global robustness
        for bridge in ["ecc-hooks-bridge", "planning-with-files-bridge", "case-bridge", "taste-bridge", "darwin-bridge", "qiushi-bridge"]:
            pkg_path = os.path.join(ext_dst, bridge, "package.json")
            if os.path.exists(pkg_path):
                pkg = load_json(pkg_path)
                if "pi-harness" not in pkg: pkg["pi-harness"] = {}
                pkg["pi-harness"]["root"] = REPO_ROOT.replace("\\", "/")
                save_json(pkg_path, pkg)
                log(f"  - {bridge} patched with absolute path")

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

if __name__ == "__main__":
    main()
