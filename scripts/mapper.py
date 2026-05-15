import os
import json
import platform
import subprocess

def load_env():
    if not os.path.exists(".harness_env.json"):
        return {}
    with open(".harness_env.json", "r") as f:
        return json.load(f)

def create_symlink(src, dest):
    """
    Creates a symbolic link. Handles Windows 'Developer Mode' or 'Run as Admin' requirements.
    """
    abs_src = os.path.abspath(src)
    abs_dest = os.path.abspath(dest)
    
    if os.path.exists(abs_dest) or os.path.islink(abs_dest):
        print(f"  [-] Removing existing {dest}...")
        if os.path.isdir(abs_dest) and not os.path.islink(abs_dest):
            import shutil
            shutil.rmtree(abs_dest)
        else:
            os.remove(abs_dest)
            
    print(f"  [+] Linking {src} -> {dest}")
    try:
        if platform.system().lower() == "windows":
            # Use cmd /c mklink to handle directory vs file correctly
            is_dir = os.path.isdir(abs_src)
            cmd = ["cmd", "/c", "mklink"]
            if is_dir:
                cmd.append("/D")
            cmd.extend([abs_dest, abs_src])
            subprocess.run(cmd, check=True, capture_output=True)
        else:
            os.symlink(abs_src, abs_dest)
        return True
    except Exception as e:
        print(f"  ❌ Failed to create link: {e}")
        return False

def map_gemini():
    print("💎 Mapping Gemini CLI projection...")
    src = "bridges/gemini/gemini-extension.json"
    dest = "gemini-extension.json"
    create_symlink(src, dest)

def map_claude():
    print("🤖 Mapping Claude Code projection...")
    src = "bridges/claude/.claude"
    dest = ".claude"
    create_symlink(src, dest)

def main():
    env = load_env()
    if not env:
        print("❌ Environment not detected. Run detector.py first.")
        return
        
    print("🚀 Starting Smart Mapping...")
    
    if env.get("gemini"):
        map_gemini()
        
    if env.get("claude"):
        map_claude()
        
    print("\n✅ Wave 3.1: Mapping Complete.")

if __name__ == "__main__":
    main()
