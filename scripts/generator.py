import json
import os
import re

def load_config():
    if not os.path.exists(".harness_env.json"):
        print("❌ Environment not detected. Run detector.py first.")
        return None, None
    with open(".harness_env.json", "r") as f:
        env = json.load(f)
    with open("core/manifest.json", "r") as f:
        manifest = json.load(f)
    return env, manifest

def translate_content(content, platform, mapping):
    """
    Translates neutral tool names like {{READ}} into platform-specific tool names.
    """
    if platform not in mapping:
        return content
        
    for tool_key, tool_name in mapping[platform].items():
        pattern = r"\{\{" + tool_key + r"\}\}"
        content = re.sub(pattern, tool_name, content)
    return content

def generate_pi(manifest):
    print("🥧 Projecting for Pi Coding Agent...")
    ext_json = {
        "name": "universal-harness-bridge-pi",
        "description": "Auto-generated universal bridge for Pi Coding Agent.",
        "version": "4.1.0",
        "author": "CK's Universal Harness",
        "commands": []
    }
    
    for cmd in manifest["commands"]:
        ext_json["commands"].append({
            "name": f"{cmd['prefix']}:{cmd['id']}",
            "description": cmd["description"],
            "location": cmd["source"]
        })
        
    os.makedirs("bridges/pi", exist_ok=True)
    with open("bridges/pi/gemini-extension.json", "w") as f:
        json.dump(ext_json, f, indent=2)
    print("✅ Created bridges/pi/gemini-extension.json")

def generate_gemini_cli(manifest):
    print("💎 Projecting for Gemini CLI...")
    base_dir = "bridges/gemini_cli/.gemini"
    cmd_base_dir = f"{base_dir}/commands"
    
    # Clean up old commands
    if os.path.exists(cmd_base_dir):
        import shutil
        shutil.rmtree(cmd_base_dir)
    os.makedirs(cmd_base_dir, exist_ok=True)
    
    for cmd in manifest["commands"]:
        # Use nested directory for namespacing (e.g. commands/omg/team.toml)
        cmd_dir = f"{cmd_base_dir}/{cmd['prefix']}"
        os.makedirs(cmd_dir, exist_ok=True)
        
        cmd_file = f"{cmd_dir}/{cmd['id']}.toml"
        
        with open(cmd['source'], "r", encoding="utf-8") as src:
            content = src.read()
            
        translated = translate_content(content, "gemini_cli", manifest["tool_mapping"])
        
        # Escape quotes for TOML
        safe_content = translated.replace('"""', '\\"\\"\\"')
        safe_desc = cmd["description"].replace('"', '\\"')
        
        # Simple format compatible with Gemini CLI v0.42
        toml_content = f'description = "{safe_desc}"\n\nprompt = """{safe_content}"""\n'
        
        with open(cmd_file, "w", encoding="utf-8") as dest:
            dest.write(toml_content)
            
    print(f"✅ Projected {len(manifest['commands'])} commands to {base_dir}/commands")
    
    # Generate root GEMINI.md for the bridge
    root_gemini = f"{base_dir}/GEMINI.md"
    with open(root_gemini, "w", encoding="utf-8") as f:
        f.write(f"""# 🚀 {manifest['harness_name']} (v{manifest['version']})

> **一鍵重建工業級 AI 開發環境** —— 已啟動 Gemini CLI 旗艦版投影。

## 🛡️ 已啟動之核心紀律 (Active Rules)
- @core/rules/agents.md
- @core/rules/cli-standards.md
- @core/rules/coding-style.md
- @core/rules/development-workflow.md
- @core/rules/git-workflow.md
- @core/rules/hooks.md
- @core/rules/patterns.md
- @core/rules/security.md
- @core/rules/testing.md

## 🏗️ 九大技術支柱 (The 9 Pillars)
1. **🛡️ 紀律守護 (Universal Hooks)**: 透過 `core/rules/hooks.md` 實施。
2. **🧠 專家直覺 (Superpowers)**: 整合 `external/superpowers`。
3. **🔍 代碼 GPS (Understand)**: 具備深度架構解讀力。
4. **📚 專案大腦 (LLM Wiki)**: 建立持久知識庫。
5. **📝 戰術持久 (Manus Planning)**: 實體化任務計畫。
6. **🏭 代理工廠 (OMC Teams)**: 透過 `/omg:team` 調度。
7. **🧪 誠信工廠 (AIxBDD)**: 透過 `/aibdd:kickoff` 啟動。
8. **🧬 自我進化 (Evolver Engine)**: 基因級優化。
9. **🧭 產品決策 (PM Skills)**: 戰略圖書館。

## ⌨️ 常用指令 (Slash Commands)
- `/omg:team` - 多代理協作
- `/aibdd:kickoff` - 啟動 BDD 流程
- `/pip:status` - 檢查任務能動性
- `/taste:standard` - 設定視覺基準

---
*本環境由 CK's Universal Harness 自動配置。*
""")
    print(f"✅ Generated {root_gemini}")

def generate_claude(manifest):
    print("🤖 Projecting for Claude Code...")
    base_dir = "bridges/claude/.claude"
    cmd_dir = f"{base_dir}/commands"
    os.makedirs(cmd_dir, exist_ok=True)
    
    for cmd in manifest["commands"]:
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
    if not env: return
    
    if env.get("pi"):
        generate_pi(manifest)
        
    if env.get("gemini_cli"):
        generate_gemini_cli(manifest)
        
    if env.get("claude"):
        generate_claude(manifest)
        
    print("\n🎉 Wave 2: Projection Complete (Calibrated).")

if __name__ == "__main__":
    main()
