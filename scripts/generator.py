import json
import os
import re

def load_config():
    with open(".harness_env.json", "r") as f:
        env = json.load(f)
    with open("core/manifest.json", "r") as f:
        manifest = json.load(f)
    return env, manifest

def translate_content(content, platform, mapping):
    """
    Translates neutral tool names like {{READ}} into platform-specific tool names.
    """
    for tool_key, tool_name in mapping[platform].items():
        pattern = r"\{\{" + tool_key + r"\}\}"
        content = re.sub(pattern, tool_name, content)
    return content

def generate_gemini(manifest):
    print("💎 Projecting for Gemini CLI...")
    ext_json = {
        "name": "universal-harness-bridge",
        "description": "Auto-generated universal bridge for Gemini CLI.",
        "version": "4.0.0",
        "author": "CK's Universal Harness",
        "commands": []
    }
    
    for cmd in manifest["commands"]:
        ext_json["commands"].append({
            "name": f"{cmd['prefix']}:{cmd['id']}",
            "description": cmd["description"],
            "location": cmd["source"]
        })
        
    os.makedirs("bridges/gemini", exist_ok=True)
    with open("bridges/gemini/gemini-extension.json", "w") as f:
        json.dump(ext_json, f, indent=2)
    print("✅ Created bridges/gemini/gemini-extension.json")

def generate_claude(manifest):
    print("🤖 Projecting for Claude Code...")
    base_dir = "bridges/claude/.claude"
    cmd_dir = f"{base_dir}/commands"
    os.makedirs(cmd_dir, exist_ok=True)
    
    for cmd in manifest["commands"]:
        # Create a proxy command file for Claude
        cmd_file = f"{cmd_dir}/{cmd['prefix']}-{cmd['id']}.md"
        with open(cmd['source'], "r", encoding="utf-8") as src:
            content = src.read()
            
        translated = translate_content(content, "claude", manifest["tool_mapping"])
        
        with open(cmd_file, "w", encoding="utf-8") as dest:
            dest.write(f"--- \n# Auto-projected from {cmd['source']}\n---\n\n")
            dest.write(translated)
            
    print(f"✅ Projected {len(manifest['commands'])} commands to {cmd_dir}")

def main():
    env, manifest = load_config()
    
    if env.get("gemini"):
        generate_gemini(manifest)
        
    if env.get("claude"):
        generate_claude(manifest)
        
    print("\n🎉 Wave 2: Projection Complete.")

if __name__ == "__main__":
    main()
