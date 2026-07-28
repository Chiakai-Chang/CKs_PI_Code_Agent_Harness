#!/usr/bin/env python3
#
# CK's Pi Code Agent Harness – Restore Configuration (Python, cross-platform)
#
# Usage:
#   python scripts/restore.py
#
import sys
import os
import re
import json
import stat
import shutil
import argparse
from datetime import datetime

# Console output contains non-ASCII status marks; legacy Windows codepages
# (e.g. cp950) crash on them when the script is run outside install.bat.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PI_DIR = os.path.join(os.path.expanduser("~"), ".pi")
AGENT_DIR = os.path.join(PI_DIR, "agent")
TIMESTAMP = datetime.now().strftime("%Y%m%dT%H%M%S")

def log(msg):
    print(f"[RESTORE] {msg}")

def log_section(title):
    """Print a section separator."""
    print()
    log(f"{'=' * 60}")
    log(f"{title}")
    log(f"{'=' * 60}")

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

DEFAULT_KEEP_BACKUPS = 5

def rotate_backups(keep_n=DEFAULT_KEEP_BACKUPS, max_age_days=28):
    """Rotate timestamped agent backups in ~/.pi/, keeping the newest keep_n backups
    and pruning backups older than max_age_days (while preserving at least 2 newest).

    Backup directories follow the naming pattern: ~/.pi/agent.backup.YYYYMMDDtHHMMSS
    Lexicographical sorting on timestamp names corresponds strictly to chronological order.
    Returns the count of pruned directories.
    """
    if keep_n < 1:
        keep_n = 1
    parent_dir = os.path.dirname(AGENT_DIR)
    prefix = os.path.basename(AGENT_DIR) + ".backup."
    if not os.path.isdir(parent_dir):
        return 0

    candidates = []
    for item in os.listdir(parent_dir):
        if item.startswith(prefix):
            full_path = os.path.join(parent_dir, item)
            if os.path.isdir(full_path):
                candidates.append(full_path)

    candidates.sort(key=lambda p: os.path.basename(p), reverse=True)

    if len(candidates) <= 2:
        return 0

    import time
    now = time.time()
    max_age_sec = max_age_days * 86400

    to_remove = []
    for idx, path in enumerate(candidates):
        if idx < 2:
            # Always retain 2 newest backups regardless of age or count
            continue
        if idx >= keep_n:
            to_remove.append(path)
            continue
        # Age check for backups past index 2 up to keep_n
        try:
            mtime = os.path.getmtime(path)
            if (now - mtime) > max_age_sec:
                to_remove.append(path)
        except OSError:
            pass

    for old_backup in to_remove:
        delete_path(old_backup)

    if to_remove:
        log(f"Pruned {len(to_remove)} old backup(s) (retained newest backups).")
    return len(to_remove)

def backup_agent(keep_n=DEFAULT_KEEP_BACKUPS):
    if not os.path.isdir(AGENT_DIR):
        return
    backup_dir = f"{AGENT_DIR}.backup.{TIMESTAMP}"
    log(f"Backing up existing agent config to: {backup_dir}")
    shutil.copytree(AGENT_DIR, backup_dir, dirs_exist_ok=True)
    rotate_backups(keep_n)

def confirm():
    if not sys.stdin.isatty():
        return True
    print()
    log("This will overwrite:")
    log("  - settings.json (merged; harness-managed keys updated)")
    log("  - models.json (merged per provider)")
    log("  - skills/* (harness-managed skills only)")
    log("  - rules/*")
    log("  - extensions/* (harness bridges only)")
    log("  - git/.gitignore")
    log("  - config.json (deprecated; will be removed)")
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

    def remove_readonly(func, p, excinfo):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except:
            pass

    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        try:
            if os.path.islink(item_path):
                try:
                    os.remove(item_path)
                except OSError:
                    try:
                        os.chmod(item_path, stat.S_IWRITE)
                        os.remove(item_path)
                    except:
                        pass
            elif os.path.isdir(item_path):
                # On Windows, junctions are isdir=True but rmtree fails
                try:
                    if sys.version_info >= (3, 12):
                        shutil.rmtree(item_path, onexc=remove_readonly)
                    else:
                        shutil.rmtree(item_path, onerror=remove_readonly)
                except OSError:
                    # Fallback for junctions
                    try: os.remove(item_path)
                    except: os.rmdir(item_path)
            else:
                try:
                    os.remove(item_path)
                except OSError:
                    try:
                        os.chmod(item_path, stat.S_IWRITE)
                        os.remove(item_path)
                    except:
                        pass
        except Exception as e:
            log(f"Warning: Failed to clear {item}: {e}")

def delete_path(path):
    """
    Safely delete a file, directory, symlink or junction.
    """
    if not os.path.lexists(path):
        return
    
    def remove_readonly(func, p, excinfo):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except:
            pass

    try:
        if os.path.islink(path) or not os.path.isdir(path):
            try:
                os.remove(path)
            except OSError:
                try:
                    os.chmod(path, stat.S_IWRITE)
                    os.remove(path)
                except:
                    pass
        else:
            try:
                if sys.version_info >= (3, 12):
                    shutil.rmtree(path, onexc=remove_readonly)
                else:
                    shutil.rmtree(path, onerror=remove_readonly)
            except OSError:
                # Fallback for junctions
                try: os.remove(path)
                except: os.rmdir(path)
    except Exception as e:
        log(f"Warning: Failed to delete {path}: {e}")

def copy_dir_contents(src, dst, exclude=None):
    ensure_dir(dst)
    for item in os.listdir(src):
        if exclude and item in exclude:
            continue
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
            return json.load(f)
    except:
        return {}

def save_json(path, data):
    ensure_dir(os.path.dirname(path) or ".")
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

# Keys owned by the harness setup wizard (scripts/setup.py). When the real
# pi-config/settings.json exists (user made explicit choices), these must win
# over whatever is already in ~/.pi/agent/settings.json — otherwise model
# switching would silently never apply.
HARNESS_MANAGED_KEYS = ["defaultModel", "defaultProvider", "apiBase", "shellPath"]

def merge_settings(existing, incoming, incoming_is_real):
    """
    Merge incoming (pi-config/settings.json) into existing (~/.pi/agent/settings.json).
    User-custom keys always survive; harness-managed keys follow the wizard's
    choices only when the incoming file is the real one (not the .example fallback).
    A missing apiBase in the real incoming file means "cloud provider" — remove
    any stale local apiBase to avoid routing confusion.
    """
    src = dict(incoming)
    if not incoming_is_real:
        # The .example template must never introduce provider/model defaults
        for key in HARNESS_MANAGED_KEYS:
            src.pop(key, None)
    merged = deep_merge(existing, src)
    if incoming_is_real:
        for key in HARNESS_MANAGED_KEYS:
            if key in incoming:
                merged[key] = incoming[key]
        if "apiBase" not in incoming and "apiBase" in merged:
            del merged["apiBase"]
    return merged

def partition_external_skills(profile_skills, ext_root):
    """Split profile_skills by source: pi_skills_root-authored ones stay
    registered directly (safe, harness-owned names); ext_root submodule ones
    carry generic upstream names and go through skill-namespace-guard's live
    collision check instead of a one-time restore-time snapshot."""
    internal = [p for p in profile_skills if not p.startswith(ext_root)]
    external = [p for p in profile_skills if p.startswith(ext_root)]
    return internal, external

# Upstream skills that fail to parse in pi and would pollute startup with
# [Skill conflicts] errors. Remove entries once fixed upstream (docs/KNOWN_ISSUES.md).
ECC_BROKEN_SKILLS = {"loop-design-check"}  # invalid YAML in description (unquoted ': ')

# Global skill directories that may conflict with harness external submodules.
# These are the exact skill names from external/taste-skill and external/superpowers
# that, if installed globally via `pi install`, will cause [Skill conflicts] warnings.
# Pruning them ensures only the local (harness-managed) versions load.
# Third-party packages that entered as residue from the author's personal ~/.pi
# dump in the initial commit and were never wired into any harness workflow.
# context-mode also exposed a plain-HTTP `ctx_fetch_and_index` tool that weak
# local models grabbed for web search and got blocked, starving the
# camofox-stealth skill. deep_merge unions lists (never removes), so emptying
# pi-config alone cannot evict these from an already-installed live settings;
# they must be pruned explicitly here.
DEPRECATED_PACKAGE_SUBSTRINGS = {"context-mode", "pi-tasks", "superpowers"}

def prune_deprecated_packages(settings):
    """Drop deprecated residue packages from settings['packages'] in place.

    deep_merge unions list entries and never removes, so a package left in an
    already-installed ~/.pi/agent/settings.json survives every restore unless
    pruned explicitly. Idempotent; safe when 'packages' is missing or non-list.
    """
    pkgs = settings.get("packages")
    if isinstance(pkgs, list):
        settings["packages"] = [
            p for p in pkgs 
            if not any(sub in p for sub in DEPRECATED_PACKAGE_SUBSTRINGS)
        ]
    return settings

# Pi renders EVERY registered skill's name + description + absolute path into
# the system prompt on every turn (engine: formatSkillsForPrompt). ECC ships
# 277 skills; registering all of them measured 110,240 chars (~27,560 tokens)
# — over half of a ~52k-token startup prompt, before the user has typed
# anything. Most are domain packs (supply-chain, prediction markets, video
# generation, Swift/Laravel/Django stacks) irrelevant to any given session.
#
# ECC upstream already classifies its skills in manifests/install-modules.json.
# Honor that taxonomy instead of globbing the directory: register the modules
# that match what this harness is for (engineering discipline + agent work),
# and leave the domain packs opt-in via harness-config.json.
ECC_DEFAULT_MODULES = [
    "workflow-quality",          # agent-sort, code-tour, continuous-learning, ...
    "agentic-patterns",          # agentic-engineering, agent-harness-construction, ...
    "security",                  # security review / compliance guidance
    "optimization-workflows",    # benchmark + latency + parallel-execution loops
]

# Registered regardless of module membership: these document the ECC
# integration itself, so dropping them would leave the bridge undiscoverable.
ECC_ALWAYS_SKILLS = ["ecc-guide", "ecc-recipes", "configure-ecc", "ecc-tools-cost-audit"]


def write_catalog(path, entries):
    """Write skill-catalog.json with ONE LINE PER SKILL.

    Pretty-printed, 104 skills came to 525 lines. Observed in a live trigger
    test: the model read it with `limit: 300`, so roughly half the catalogue was
    invisible in the read it actually performed. One line per entry keeps the
    whole catalogue inside a single default read.
    """
    ensure_dir(os.path.dirname(path))
    lines = ['{', '  "version": 1,', '  "skills": [']
    for i, e in enumerate(entries):
        comma = "," if i < len(entries) - 1 else ""
        lines.append("    " + json.dumps(e, ensure_ascii=False) + comma)
    lines += ["  ]", "}"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def manifest_path_of(repo_root):
    return os.path.join(repo_root, "pi-config", "external-skills-manifest.json")


def skill_frontmatter(skill_md_path):
    """Return (name, description) from a SKILL.md, or (None, None)."""
    try:
        with open(skill_md_path, encoding="utf-8", errors="replace") as f:
            raw = f.read()
    except OSError:
        return (None, None)
    m = re.match(r"^---\r?\n([\s\S]*?)\r?\n---", raw)
    if not m:
        return (None, None)
    body = m.group(1)
    nm = re.search(r"^name:\s*(.+?)\s*$", body, re.M)
    # \Z, not $: under re.M a `$` terminates at the first line end, which would
    # cut every multi-line YAML description down to its first line. Pi reads the
    # whole thing, so a truncated copy in the catalog would misrepresent the
    # skill to the model exactly where it is deciding whether to load it.
    ds = re.search(r"^description:\s*([\s\S]+?)(?=\n[A-Za-z_-]+:\s|\Z)", body, re.M)
    # YAML allows a quoted scalar, and at least one upstream skill uses it
    # (`name: "yes"`). Leaving the quotes on means the name never matches a
    # core-list entry and the skill silently falls to the catalog.
    name = nm.group(1).strip().strip("\"'") if nm else None
    desc = " ".join(ds.group(1).split()) if ds else ""
    return (name, desc)


def discover_skills(roots):
    """Walk skill roots and return [(name, description, skill_md_path, dir)].

    A registered path may be a single skill or a container of them, so this
    walks rather than assuming one level (same shape Pi's own discovery uses).
    """
    found = []
    seen = set()
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            if "SKILL.md" not in filenames:
                continue
            skill_md = os.path.join(dirpath, "SKILL.md")
            if skill_md in seen:
                continue
            seen.add(skill_md)
            name, desc = skill_frontmatter(skill_md)
            if not name:
                name = os.path.basename(dirpath)
            found.append((name, desc, skill_md.replace("\\", "/"), dirpath.replace("\\", "/")))
    return found


def skill_tiers_from_config(harness_config_path):
    """Read skillTiers from harness-config.json.

    Returns ("all", []) to register everything natively (today's behaviour), or
    ("tiered", [core names]). Anything unparseable falls back to "all": losing
    every long-tail skill silently is far worse than a fat prompt, the same
    fail-open choice ecc_skill_paths() makes.
    """
    try:
        with open(harness_config_path, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        return ("all", [])
    tiers = cfg.get("skillTiers")
    if not isinstance(tiers, dict):
        return ("all", [])
    if tiers.get("mode") != "tiered":
        return ("all", [])
    core = tiers.get("core")
    if not isinstance(core, list) or not all(isinstance(c, str) for c in core):
        return ("all", [])
    return ("tiered", core)


def partition_skills_by_tier(skills, core_names):
    """Split discovered skills into (core, tail) by skill name.

    Core skills stay natively registered with their full description, so Pi's
    own discovery path is untouched for them. Tail skills are surfaced by
    skill-catalog-bridge as an inline name list instead — Pi charges ~213 chars
    of fixed overhead (XML tags + absolute path) per natively registered skill
    regardless of description length, so the only way to reclaim it is to not
    register the skill.
    """
    wanted = set(core_names)
    core = [s for s in skills if s[0] in wanted]
    tail = [s for s in skills if s[0] not in wanted]
    return core, tail


def ecc_modules_from_config(harness_config_path):
    """Read eccSkillModules from pi-config/harness-config.json.

    Values: a list of ECC module ids, "all" for the full 277-skill set, or
    absent for ECC_DEFAULT_MODULES. Malformed config falls back to the default
    rather than failing the restore.
    """
    try:
        with open(harness_config_path, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        return ECC_DEFAULT_MODULES
    value = cfg.get("eccSkillModules")
    if value == "all":
        return "all"
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return value
    return ECC_DEFAULT_MODULES


def ecc_skill_paths(ecc_skills_root, modules=None):
    """
    Enumerate the ECC skills selected by `modules` (a list of ECC module ids,
    or "all"). Known-broken upstream skills are skipped without modifying the
    submodule. Falls back to registering the root directory when the submodule
    is not initialized yet.
    """
    if not os.path.isdir(ecc_skills_root):
        return [ecc_skills_root.replace("\\", "/")]

    if modules is None:
        modules = ECC_DEFAULT_MODULES

    selected = None  # None == no filtering (register everything)
    if modules != "all":
        manifest = os.path.join(
            os.path.dirname(ecc_skills_root), "manifests", "install-modules.json"
        )
        try:
            with open(manifest, encoding="utf-8") as f:
                mods = json.load(f)["modules"]
        except (OSError, ValueError, KeyError, TypeError):
            # No manifest (submodule not updated / upstream reshuffle): fail
            # open to the full set rather than silently dropping every ECC
            # skill, which would be a much worse surprise than a fat prompt.
            log("  ! ECC install-modules.json unreadable — registering all ECC skills")
            mods = None
        if mods is not None:
            wanted = set(modules)
            selected = set(ECC_ALWAYS_SKILLS)
            for m in mods:
                if m.get("id") not in wanted:
                    continue
                for p in m.get("paths", []):
                    if p.startswith("skills/"):
                        selected.add(p.split("/", 1)[1])

    paths = []
    for name in sorted(os.listdir(ecc_skills_root)):
        if name in ECC_BROKEN_SKILLS:
            continue
        if selected is not None and name not in selected:
            continue
        p = os.path.join(ecc_skills_root, name)
        if os.path.isdir(p) and os.path.exists(os.path.join(p, "SKILL.md")):
            paths.append(p.replace("\\", "/"))
    return paths

def merge_models(existing, incoming):
    """Merge models.json at provider granularity so user-defined providers survive."""
    merged = dict(existing) if existing else {}
    providers = dict(merged.get("providers", {}) or {})
    providers.update(incoming.get("providers", {}) or {})
    for k, v in incoming.items():
        if k != "providers":
            merged[k] = v
    merged["providers"] = providers
    return merged

# Older setup.py wrote maxTokens=4096 regardless of context size; on
# large-context (thinking) models that truncates long responses mid-answer
# ("maximum output token limit").
LEGACY_DEFAULT_MAX_TOKENS = 4096

def heal_max_tokens(models):
    """Raise maxTokens left at the legacy 4096 default on large-context models.

    Scales to contextWindow // 8, ceiling 32768 (runaway-generation brake).
    Only the exact legacy default is touched so user-chosen values survive.
    Returns the ids of healed models.
    """
    healed = []
    for provider in (models.get("providers") or {}).values():
        for model in provider.get("models") or []:
            ctx = model.get("contextWindow") or 0
            scaled = min(ctx // 8, 32768)
            if model.get("maxTokens") == LEGACY_DEFAULT_MAX_TOKENS and scaled > LEGACY_DEFAULT_MAX_TOKENS:
                model["maxTokens"] = scaled
                healed.append(model.get("id"))
    return healed

def check_models_against_server(models, probe=None):
    """Compare declared model specs against the live local server's truth.

    models.json is a snapshot; server restarts change reality (e.g. llama.cpp
    -np 2 splits a 262144 context into 2 slots of 131072 each, and pi then
    overruns the real per-request window without knowing). Probes only
    localhost providers; a server that is not running is a normal situation
    and stays silent. Returns human-readable warnings, never raises.
    """
    if probe is None:
        from setup import probe_llama_cpp as probe  # same directory
    warnings = []
    for provider in (models.get("providers") or {}).values():
        base = provider.get("baseUrl") or ""
        if not ("127.0.0.1" in base or "localhost" in base):
            continue
        try:
            live = probe(base)
        except Exception:
            live = None
        if not live or not live.get("ctx"):
            continue
        for model in provider.get("models") or []:
            declared = model.get("contextWindow") or 0
            if declared > live["ctx"]:
                warnings.append(
                    f"{model.get('id')}: contextWindow {declared} exceeds the server's "
                    f"current per-request context {live['ctx']} — long sessions will "
                    f"overrun it. Lower contextWindow or restart the server with a "
                    f"bigger context (fewer slots)."
                )
    return warnings

def main():
    parser = argparse.ArgumentParser(description="CK's Pi Code Agent Harness - Restore")
    parser.add_argument("--auto", action="store_true", help="Skip confirmation")
    parser.add_argument("--profile", choices=["minimal", "standard"], default="standard", help="Skill profile to load")
    parser.add_argument("--config-only", action="store_true",
                        help="Only sync settings.json / models.json; do not touch skills, rules, extensions or profile registration")
    parser.add_argument("--keep-backups", type=int, default=DEFAULT_KEEP_BACKUPS,
                        help=f"Number of newest backups to retain during update (default: {DEFAULT_KEEP_BACKUPS})")
    args = parser.parse_args()

    # Check environment variable as a robust fallback for --auto
    is_auto = args.auto or (os.environ.get("PI_AUTO_RESTORE") == "1")
    profile = args.profile or os.environ.get("PI_HARNESS_PROFILE", "standard")

    log_section("CK's Pi Code Agent Harness – Restore Configuration")
    log(f"Repo root: {REPO_ROOT}")
    log(f"Agent dir: {AGENT_DIR}")
    log(f"Profile:   {profile}{' (config-only)' if args.config_only else ''}")
    print()

    ensure_dir(AGENT_DIR)
    ensure_dir(os.path.join(AGENT_DIR, "skills"))
    ensure_dir(os.path.join(AGENT_DIR, "rules"))
    ensure_dir(os.path.join(AGENT_DIR, "extensions"))
    ensure_dir(os.path.join(AGENT_DIR, "git"))

    backup_agent(keep_n=args.keep_backups)

    if not is_auto and not confirm():
        log("Abated by user.")
        sys.exit(0)

    # Config
    log("Restoring config (settings, models, git)...")

    # 1. Load and merge settings.json
    settings_dest = os.path.join(AGENT_DIR, "settings.json")
    settings_src = os.path.join(REPO_ROOT, "pi-config", "settings.json")

    settings = {}
    if os.path.exists(settings_dest):
        settings = load_json(settings_dest)

    # Only the real settings.json (written by setup.py after explicit user
    # choices) may override harness-managed keys; the .example fallback must not.
    settings_src_is_real = os.path.exists(settings_src)
    default_settings = load_json(settings_src)
    settings = merge_settings(settings, default_settings, settings_src_is_real)

    # Evict deprecated residue packages (deep_merge never prunes list entries).
    prune_deprecated_packages(settings)

    if "env" not in settings: settings["env"] = {}
    settings["env"]["PI_HARNESS_ROOT"] = REPO_ROOT.replace("\\", "/")

    # 2. Dynamic Submodule Paths Resolution
    ext_root = os.path.join(REPO_ROOT, "external").replace("\\", "/")
    pi_skills_root = os.path.join(REPO_ROOT, "pi-skills").replace("\\", "/")
    pi_extensions_root = os.path.join(REPO_ROOT, "pi-extensions").replace("\\", "/")

    profile_skills = []
    profile_extensions = []
    profile_prompts = []

    # Minimal profile
    if profile == "minimal":
        profile_skills.append(os.path.join(ext_root, "caveman", "skills", "caveman").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "ecc-hooks-bridge").replace("\\", "/"))

    # Standard profile (Default)
    elif profile == "standard":
        # Local browser skills
        profile_skills.append(os.path.join(pi_skills_root, "chrome-cdp").replace("\\", "/"))
        profile_skills.append(os.path.join(pi_skills_root, "dev-browser").replace("\\", "/"))

        # Caveman skills
        for name in ["caveman", "caveman-commit", "caveman-review", "caveman-compress", 
                     "caveman-stats", "caveman-help", "cavecrew"]:
            profile_skills.append(os.path.join(ext_root, "caveman", "skills", name).replace("\\", "/"))
        
        # Superpowers skills: registered directly from external/superpowers/skills/
        # so all 14 superpowers skills are available as standard harness-managed skills
        # without loading the obra/superpowers extension (which polluted prompts with XML tags).
        sp_skills_dir = os.path.join(ext_root, "superpowers", "skills")
        if os.path.isdir(sp_skills_dir):
            for sp_name in sorted(os.listdir(sp_skills_dir)):
                sp_path = os.path.join(sp_skills_dir, sp_name)
                if os.path.isdir(sp_path):
                    profile_skills.append(sp_path.replace("\\", "/"))
            
        profile_skills.append(os.path.join(ext_root, "karpathy-skills", "skills", "karpathy-guidelines").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "planning-with-files", ".pi", "skills", "planning-with-files").replace("\\", "/"))
        profile_prompts.append(os.path.join(ext_root, "planning-with-files", "commands").replace("\\", "/"))
        # /browse — deterministic camofox-stealth entry point (does not rely on the
        # model auto-discovering the skill; weak local models routinely fail to).
        profile_prompts.append(os.path.join(pi_skills_root, "optional", "camofox-stealth", "commands").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "llm-wiki-plugin", "skills", "llm-wiki").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "prompt-master").replace("\\", "/"))
        ecc_modules = ecc_modules_from_config(
            os.path.join(REPO_ROOT, "pi-config", "harness-config.json")
        )
        ecc_paths = ecc_skill_paths(os.path.join(REPO_ROOT, "external", "ecc", "skills"), ecc_modules)
        profile_skills.extend(ecc_paths)
        log("  - ECC skills: %d registered (modules: %s)"
            % (len(ecc_paths), "all" if ecc_modules == "all" else ", ".join(ecc_modules)))
        profile_skills.append(os.path.join(ext_root, "Local-Agent-Workspace").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "taste-skill", "skills").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "darwin-skill").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "qiushi-skill", "skills").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "agents-best-practices").replace("\\", "/"))
        profile_skills.append(os.path.join(pi_skills_root, "graphify").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "evolver").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "yes.md", "skills").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "loopy", "skills").replace("\\", "/"))
        profile_skills.append(os.path.join(ext_root, "mece-autopilot", "skills", "mece-autopilot").replace("\\", "/"))

        # Extensions
        profile_extensions.append(os.path.join(pi_extensions_root, "ecc-hooks-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "planning-with-files-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "case-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "taste-bridge").replace("\\", "/"))
        profile_extensions.append(os.path.join(pi_extensions_root, "mece-autopilot-bridge").replace("\\", "/"))
        # Surfaces the long-tail skills that tiered registration keeps out of
        # the natively-registered set (no-op when skillTiers mode is "all").
        profile_extensions.append(os.path.join(pi_extensions_root, "skill-catalog-bridge").replace("\\", "/"))
        # Sequential subagent fan-out; keeps page content out of the main context.
        profile_extensions.append(os.path.join(pi_extensions_root, "deep-research-bridge").replace("\\", "/"))
        # Exposes camofox-stealth as first-class web_search/web_open tools so weak
        # models call them reflexively instead of denying they can browse.
        profile_extensions.append(os.path.join(pi_extensions_root, "stealth-web-bridge").replace("\\", "/"))
        # Wires YES.md pre-bash-guard: deterministic block on destructive shell
        # commands (rm -rf /, git push --force, DROP TABLE, ...). Enforcement the
        # model can't ignore — valuable especially with uncensored local models.
        profile_extensions.append(os.path.join(pi_extensions_root, "yes-hooks-bridge").replace("\\", "/"))

    # 2a. Partition external/* skills out of profile_skills: they carry generic
    # upstream names and can silently shadow anything the user independently
    # installs later. skill-namespace-guard live-detects collisions with them
    # at every session start instead of restore.py deciding once, frozen.
    profile_skills, profile_skills_external = partition_external_skills(profile_skills, ext_root)

    # 2b. Tier the external skills. Pi renders name + description + absolute
    # path for every registered skill into EVERY turn's system prompt
    # (formatSkillsForPrompt); 145 skills measured at 55,239 chars (~13,809
    # tokens per turn, 58% of the whole prompt). Core skills stay natively
    # registered; the long tail is surfaced by skill-catalog-bridge as an
    # inline name list. See docs/superpowers/specs/
    # 2026-07-28-tiered-skill-registration-design.md.
    harness_cfg = os.path.join(REPO_ROOT, "pi-config", "harness-config.json")
    tier_mode, core_names = skill_tiers_from_config(harness_cfg)
    catalog_path = os.path.join(REPO_ROOT, "pi-config", "skill-catalog.json")

    if tier_mode == "tiered":
        discovered = discover_skills(profile_skills_external)
        core, tail = partition_skills_by_tier(discovered, core_names)
        # Register the directory of each core skill; the tail is not registered.
        core_dirs = sorted({d for _n, _d, _p, d in core})
        # Name and path ONLY — deliberately no descriptions. Reading the
        # catalogue is a tool result the model swallows whole: with
        # descriptions the file was 42,229 chars (~10,557 tokens), and in a live
        # trigger test the model read it, its prompt jumped 16,613 -> 27,715
        # tokens, and its very next turn answered a question that was never
        # asked. A mechanism built to save ~11,500 tokens per turn must not dump
        # ~10,700 into the context the moment it is used. The description is
        # redundant anyway: the model reads the SKILL.md next, which opens with it.
        tail_entries = [{"name": n, "path": p} for n, _d, p, _dir in sorted(tail)]
        write_catalog(catalog_path, tail_entries)
        save_json(manifest_path_of(REPO_ROOT), [{"path": p} for p in core_dirs])
        log(f"  - skill tiers: {len(core_dirs)} core registered, {len(tail_entries)} in catalog")
        # A core entry that matches nothing is a typo or an upstream rename, and
        # its only symptom is a skill quietly demoted to the catalog. Name it.
        internal = {os.path.basename(os.path.dirname(p)) for p in
                    [os.path.join(d, "SKILL.md") for _n, _d, _p, d in discovered]}
        unmatched = [c for c in core_names
                     if c not in {n for n, _d, _p, _dir in discovered} and c not in internal]
        if unmatched:
            log(f"  ! skillTiers.core names not found among external skills "
                f"(harness-internal pi-skills/ are always registered, so those are fine): "
                f"{', '.join(sorted(unmatched))}")
    else:
        save_json(manifest_path_of(REPO_ROOT), [{"path": p} for p in profile_skills_external])
        # An empty catalog keeps the bridge a no-op rather than leaving a stale
        # list injected after someone switches back to mode "all".
        save_json(catalog_path, {"version": 1, "skills": []})
        log(f"  - external-skills-manifest.json written ({len(profile_skills_external)} entries)")

    # skill-namespace-guard re-registers the external/* skills above (collision-
    # checked, live) — required regardless of profile since minimal also has an
    # ext_root skill (caveman).
    profile_extensions.append(os.path.join(pi_extensions_root, "skill-namespace-guard").replace("\\", "/"))

    # compact-continuation-bridge: Pi's own compact() never auto-retries except
    # for overflow recovery, so any /compact, threshold auto-compact, or
    # extension-triggered ctx.compact() leaves the agent idle mid-task with no
    # nudge to continue. Applies regardless of profile — compaction can happen
    # in any session, not just standard-profile ones.
    profile_extensions.append(os.path.join(pi_extensions_root, "compact-continuation-bridge").replace("\\", "/"))

    # 3. Filter existing settings to keep user's custom skills/extensions not managed by Harness
    # (skipped in --config-only mode: keep whatever profile is already registered)
    if not args.config_only:
        existing_skills = settings.get("skills", [])
        clean_skills = [p for p in existing_skills if not p.replace("\\", "/").startswith(REPO_ROOT.replace("\\", "/"))]
        for s in profile_skills:
            if s not in clean_skills:
                clean_skills.append(s)
        settings["skills"] = clean_skills

        existing_extensions = settings.get("extensions", [])
        internal_bridge_names = ["ecc-hooks-bridge", "planning-with-files-bridge", "case-bridge", "taste-bridge", "mece-autopilot-bridge", "stealth-web-bridge", "yes-hooks-bridge", "skill-namespace-guard", "compact-continuation-bridge", "skill-catalog-bridge", "deep-research-bridge"]
        clean_extensions = []
        for p in existing_extensions:
            p_normalized = p.replace("\\", "/").lower()
            if p_normalized.startswith(REPO_ROOT.replace("\\", "/").lower()):
                continue
            is_internal = False
            for name in internal_bridge_names:
                if name in p_normalized:
                    is_internal = True
                    break
            if not is_internal:
                clean_extensions.append(p)
        # Unlike profile_skills/profile_prompts, profile_extensions is NOT
        # appended here. Every entry in profile_extensions gets physically
        # copytree'd into ~/.pi/agent/extensions/<bridge>/ further below,
        # which Pi auto-discovers by directory (~/.pi/agent/extensions/*/
        # index.ts) regardless of this settings.json array. Also listing the
        # repo-path source here made Pi load each bridge from BOTH locations
        # at once — registerTool() calls collided ("Tool web_search conflicts
        # with ...") and pi failed to start. This array staying clear of
        # harness-managed bridges is correct, not a bug: only genuinely
        # extra, non-copied user extensions belong here.
        settings["extensions"] = clean_extensions

        existing_prompts = settings.get("prompts", [])
        clean_prompts = [p for p in existing_prompts if not p.replace("\\", "/").startswith(REPO_ROOT.replace("\\", "/"))]
        for pr in profile_prompts:
            if pr not in clean_prompts:
                clean_prompts.append(pr)
        settings["prompts"] = clean_prompts

    save_json(settings_dest, settings)
    log("  - settings.json updated" + ("" if args.config_only else " with submodule paths"))

    # Sync models.json (merge per provider so user-defined providers survive)
    models_src = os.path.join(REPO_ROOT, "pi-config", "models.json")
    if os.path.exists(models_src):
        models_data = load_json(models_src)
        if models_data:
            models_dest = os.path.join(AGENT_DIR, "models.json")
            existing_models = load_json(models_dest) if os.path.exists(models_dest) else {}
            merged_models = merge_models(existing_models, models_data)
            healed = heal_max_tokens(merged_models)
            save_json(models_dest, merged_models)
            log("  - models.json synced (merged)")
            for mid in healed:
                log(f"  - {mid}: maxTokens raised from legacy 4096 to fit contextWindow")
            for warning in check_models_against_server(merged_models):
                log(f"  ! {warning}")

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

    if args.config_only:
        print()
        log("✅ Config-only sync complete (skills/rules/extensions untouched).")
        return

    # Core skills (always)
    log("Restoring core skills...")
    core_src = os.path.join(REPO_ROOT, "pi-skills", "core")
    skills_dst = os.path.join(AGENT_DIR, "skills")
    
    # We selectively delete only the skills that are managed by the harness,
    # rather than wiping the entire directory, to preserve user's own custom skills.
    managed_skills = ["hello-reflect", "planning-with-files", "camofox", "camofox-stealth", "cua-commander", "nothing-design", "adversary-review", "contrarian-review", "browser-automation-guide", "deep-research-guide", "autonomous-experiment-guide", "tool-repair-guide", "guardian-pipeline-guide", "subagent-orchestration-guide", "workflow-os-guide", "grilling-protocol", "harness-factory-guide", "ide-intelligence-guide", "minimal-prompt-guide", "bridges"]
    for s_name in managed_skills:
        delete_path(os.path.join(skills_dst, s_name))

    if os.path.isdir(core_src):
        # "bridges" holds RATIONALE decision docs, not skills — keep it out of the agent dir
        # Also exclude "planning-with-files" because external submodule version is preferred
        copy_dir_contents(core_src, skills_dst, exclude={"bridges", "planning-with-files"})
    else:
        log("Core skills directory not found, skipping.")

    # Optional skills (design / heavy) – prompt
    optional_src = os.path.join(REPO_ROOT, "pi-skills", "optional")
    restore_optional = True

    if os.path.isdir(optional_src) and sys.stdin.isatty() and profile == "standard" and not is_auto:
        print()
        log("This repo includes optional design/creative skills (heavier).")
        log("Examples: design, ui-ux-pro-max, ui-styling, slides, brand, etc.")
        sys.stdout.flush()
        ans = input("[RESTORE] Restore optional skills? (Y/n): ").strip().lower()
        if ans in ("n", "no"):
            restore_optional = False

    if restore_optional and os.path.isdir(optional_src) and profile == "standard":
        log("Restoring optional skills...")
        copy_dir_contents(optional_src, skills_dst)
    else:
        log("Optional skills skipped (or not standard profile).")

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
        # We selectively delete only the bridges managed by this harness to preserve other extensions.
        for bridge in ["ecc-hooks-bridge", "planning-with-files-bridge", "case-bridge", "taste-bridge", "mece-autopilot-bridge", "stealth-web-bridge", "yes-hooks-bridge", "skill-namespace-guard", "compact-continuation-bridge", "skill-catalog-bridge", "deep-research-bridge"]:
            delete_path(os.path.join(ext_dst, bridge))
            
        for ext_path in profile_extensions:
            bridge = os.path.basename(ext_path)
            src_bridge = os.path.join(ext_src, bridge)
            dst_bridge = os.path.join(ext_dst, bridge)
            if os.path.isdir(src_bridge):
                shutil.copytree(src_bridge, dst_bridge, dirs_exist_ok=True)
                
                # Patch bridges with absolute path for global robustness
                pkg_path = os.path.join(dst_bridge, "package.json")
                if os.path.exists(pkg_path):
                    pkg = load_json(pkg_path)
                    if "pi-harness" not in pkg: pkg["pi-harness"] = {}
                    pkg["pi-harness"]["root"] = REPO_ROOT.replace("\\", "/")
                    save_json(pkg_path, pkg)
                    
                # Validate TS syntax with Node --check to prevent startup crash
                index_ts = os.path.join(dst_bridge, "index.ts")
                if os.path.exists(index_ts):
                    try:
                        res = subprocess.run(["node", "--check", index_ts], capture_output=True, text=True)
                        if res.returncode != 0:
                            log(f"  ❌ Syntax Error in {bridge}: {res.stderr.strip()}")
                        else:
                            log(f"  - {bridge} verified (syntax OK)")
                    except Exception:
                        log(f"  - {bridge} patched with absolute path")
                else:
                    log(f"  - {bridge} patched with absolute path")

    print()
    log_section("✅ Restore Complete")
    log("All configuration files have been restored.")
    
    print()
    log("📌 Next steps:")
    log("  1) Ensure Pi is installed:")
    log("     - npm install -g @earendil-works/pi-coding-agent")
    log("  2) Update Pi to latest:")
    log("     - pi update")
    log("  3) Open Pi and confirm:")
    log("     - Skills loaded without conflicts")
    log("     - Extensions loaded")
    print()

if __name__ == "__main__":
    main()
