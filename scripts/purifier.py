import os
import shutil
import json
import platform
from datetime import datetime

def get_home_dirs():
    home = os.path.expanduser("~")
    return {
        "gemini": os.path.join(home, ".gemini"),
        "claude": os.path.join(home, ".claude"),
        "codex": os.path.join(home, ".codex")
    }

def backup_legacy_env(platform_name, legacy_path):
    if not os.path.exists(legacy_path):
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{legacy_path}.legacy_{timestamp}"
    
    print(f"  [📦] Backing up legacy {platform_name} to {backup_path}...")
    shutil.move(legacy_path, backup_path)
    return backup_path

def restore_essential_configs(backup_path, new_path):
    """
    Extracts and restores essential configuration files from backup.
    """
    essentials = ["auth.json", "models.json", "settings.json", "config.json"]
    os.makedirs(new_path, exist_ok=True)
    
    restored_count = 0
    for file in essentials:
        src = os.path.join(backup_path, file)
        if os.path.exists(src):
            print(f"    [✨] Restoring {file} from legacy backup...")
            shutil.copy2(src, os.path.join(new_path, file))
            restored_count += 1
            
    return restored_count

def run_purification(force=False):
    print("🧹 Starting Environment Purification...")
    legacy_dirs = get_home_dirs()
    
    summary = {
        "purified": [],
        "restored_files": 0
    }
    
    for platform, path in legacy_dirs.items():
        if os.path.exists(path):
            if not force:
                print(f"  [⚠️] Detected existing {platform} environment at {path}")
                continue
            
            backup = backup_legacy_env(platform, path)
            if backup:
                restored = restore_essential_configs(backup, path)
                summary["purified"].append(platform)
                summary["restored_files"] += restored
                
    return summary

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Execute purification without prompt.")
    args = parser.parse_args()
    
    if not args.force:
        print("🔍 Scanning for legacy AI environments...")
        legacy_dirs = get_home_dirs()
        found = [p for p, d in legacy_dirs.items() if os.path.exists(d)]
        
        if not found:
            print("✅ No legacy environments detected. Clean slate.")
            return
            
        print(f"Found existing environments: {', '.join(found)}")
        ans = input("\nDo you want to perform a 'Clean Reinstall' (Backup + Sanitized Restore)? [y/N]: ").strip().lower()
        if ans != 'y':
            print("Purification skipped.")
            return

    results = run_purification(force=True)
    print(f"\n🎉 Purification Complete: {len(results['purified'])} platforms cleaned, {results['restored_files']} configs inherited.")

if __name__ == "__main__":
    main()
