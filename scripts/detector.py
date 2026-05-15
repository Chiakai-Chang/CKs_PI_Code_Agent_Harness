import shutil
import os
import json

def detect_platforms():
    """
    Detects which AI CLI platforms are available in the current environment.
    Returns a dictionary of platform status.
    """
    platforms = {
        "pi": False,
        "gemini_cli": False,
        "claude": False,
        "codex": False
    }
    
    # Detect 'pi' (Pi Coding Agent)
    if shutil.which("pi"):
        platforms["pi"] = True
        
    # Detect 'gemini' (Gemini CLI)
    if shutil.which("gemini"):
        platforms["gemini_cli"] = True
        
    # Detect 'claude' (Claude Code)
    if shutil.which("claude"):
        platforms["claude"] = True
        
    # Detect 'codex' (Codex CLI)
    if shutil.which("codex"):
        platforms["codex"] = True
        
    return platforms

def main():
    print("🔍 Probing environment for AI CLI platforms...")
    status = detect_platforms()
    
    for platform, installed in status.items():
        icon = "✅" if installed else "❌"
        print(f"{icon} {platform.upper()}")
        
    # Write detection result to a temp state file
    with open(".harness_env.json", "w") as f:
        json.dump(status, f, indent=2)
    
    print("\nEnvironment status saved to .harness_env.json")

if __name__ == "__main__":
    main()
