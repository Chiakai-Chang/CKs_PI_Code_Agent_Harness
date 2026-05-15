#!/usr/bin/env python3
#
# CK's Pi Code Agent Harness - Flagship Setup Script (v3.7.2)
#
# Domains: Environment, Hardware, LLM Probe, Spec Recommendation, Orchestration
#

import sys
import os
import platform
import subprocess
import json
import shutil
import time
import urllib.request
import urllib.error
import webbrowser
import argparse
import re

# --- Globals & Paths ---
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PI_CONFIG_DIR = os.path.join(REPO_ROOT, "pi-config")
SETTINGS_PATH = os.path.join(PI_CONFIG_DIR, "settings.json")
HARNESS_CONFIG_PATH = os.path.join(PI_CONFIG_DIR, "harness-config.json")
AUTO_MODE = False

# --- Core Utility Domain ---

def run(cmd):
    """Run shell command with triple-encoding fallback for cross-platform robustness."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=False, check=False)
        # Try different encodings for Windows (UTF-16 is common for wmic, CP65001 for UTF-8)
        for enc in ['cp65001', 'utf-16', 'utf-8', 'gbk']:
            try:
                stdout = r.stdout.decode(enc).strip()
                stderr = r.stderr.decode(enc).strip()
                if stdout or r.returncode == 0:
                    return r.returncode == 0, stdout, stderr
            except: continue
        return r.returncode == 0, r.stdout.decode(errors='replace').strip(), r.stderr.decode(errors='replace').strip()
    except Exception as e:
        return False, "", str(e)

def run_stream(cmd):
    """Run command and stream output to terminal."""
    print(f"  $ {cmd.strip()}")
    try:
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
        proc.wait()
        return proc.returncode == 0
    except: return False

def is_admin():
    if platform.system().lower() == "windows":
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except: return False
    return os.geteuid() == 0

def has_command(cmd):
    ok, _, _ = run(f"{cmd} --version")
    return ok

def load_json(path):
    if not os.path.exists(path):
        example = path + ".example"
        if os.path.exists(example): path = example
        else: return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

# --- Environment Domain ---

def suggest_git(p):
    if p == "windows": print("  => winget install Git.Git")
    elif p == "macos": print("  => brew install git")
    else: print("  => sudo apt install -y git")

def suggest_node(p):
    if p == "windows": print("  => Install nvm-windows from GitHub")
    else: print("  => curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash")

def detect_git_bash():
    if platform.system().lower() != "windows": return None
    paths = [
        os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Git", "bin", "bash.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Git", "bin", "bash.exe"),
    ]
    for p in paths:
        if os.path.exists(p): return p
    return None

# --- Hardware Domain (Fixed ??GB) ---

def get_hardware_info():
    """Gather physical RAM and VRAM using robust number extraction."""
    info = {"ram": None, "vram": None}
    p = platform.system().lower()
    try:
        if p == "windows":
            # Primary: wmic (fast)
            ok, out, _ = run("wmic computersystem get TotalPhysicalMemory")
            nums = [int(n) for n in re.findall(r'\d+', out) if int(n) > 1024**3]
            if nums: info["ram"] = nums[0] // (1024**3)
            # Fallback: powershell
            if not info["ram"]:
                ok, out, _ = run("powershell -Command \"(Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum\"")
                nums = re.findall(r'\d+', out)
                if nums: info["ram"] = int(nums[0]) // (1024**3)
        else:
            with open("/proc/meminfo", "r") as f:
                content = f.read()
                m = re.search(r"MemTotal:\s+(\d+)\s+kB", content)
                if m: info["ram"] = int(m.group(1)) // (1024**2)
    except: pass

    try:
        ok, out, _ = run("nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits")
        if ok and out:
            vrams = [int(x) for x in re.findall(r'\d+', out)]
            if vrams: info["vram"] = sum(vrams) // 1024
    except: pass
    return info

# --- LLM Probe Domain (Truth-Finding) ---

def probe_ollama():
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1) as response:
            data = json.loads(response.read().decode())
            return [("ollama", m["name"]) for m in data.get("models", [])]
    except: return []

def probe_llama_cpp(url):
    """Deep probe for n_ctx truth via /props and /slots."""
    base = url.replace("localhost", "127.0.0.1").rstrip("/")
    # 1. Try /props
    try:
        with urllib.request.urlopen(f"{base}/props", timeout=1) as resp:
            data = json.loads(resp.read().decode())
            ctx = data.get("default_generation_settings", {}).get("n_ctx")
            if not ctx: ctx = data.get("n_ctx")
            name = os.path.basename(data.get("model_path", "unknown"))
            if ctx: return {"name": name, "ctx": int(ctx)}
    except: pass
    # 2. Try /slots
    try:
        with urllib.request.urlopen(f"{base}/slots", timeout=1) as resp:
            data = json.loads(resp.read().decode())
            if isinstance(data, list) and len(data) > 0:
                ctx = data[0].get("n_ctx")
                if ctx: return {"name": "Detected Slot", "ctx": int(ctx)}
    except: pass
    return None

def detect_llm_services():
    models = probe_ollama()
    for port in [1234, 8080, 8000, 3000]:
        url = f"http://127.0.0.1:{port}"
        p = probe_llama_cpp(url)
        if p: models.append((url, p["name"]))
    return models

# --- Spec Domain (Truth-First) ---

def get_recommended_specs(model_id, hw, api_base=None, provider=None):
    """The intelligence core: Respect API truth over heuristics."""
    mid = (model_id or "").lower()
    ctx, max_t, reasoning, is_truth = 8192, 4096, False, False
    
    # 1. Fetch Real Truth
    meta = {}
    if provider == "ollama":
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/show", data=json.dumps({"name": model_id}).encode())
            with urllib.request.urlopen(req, timeout=1) as resp:
                data = json.loads(resp.read().decode())
                m = re.search(r'num_ctx\s+(\d+)', data.get("parameters", ""))
                if m: meta["ctx"] = int(m.group(1))
        except: pass
    elif api_base:
        p = probe_llama_cpp(api_base)
        if p: meta["ctx"] = p["ctx"]

    if meta.get("ctx"):
        ctx, is_truth = meta["ctx"], True

    # 2. Reasoning Detection
    if any(k in mid for k in ["r1", "thought", "qwen"]): reasoning = True

    # 3. Fallback Heuristics (ONLY if no truth)
    if not is_truth:
        if "qwen" in mid: ctx = 32768
        if "3.6" in mid: ctx = 196608 # Only a suggestion for fresh setup
        
        # Size based
        m = re.search(r'(\d+)b', mid)
        if m:
            size = int(m.group(1))
            if size >= 70: ctx = 32768; max_t = 8192
            elif size >= 27: ctx = 131072; max_t = 16384

    # 4. Downward Safety Capping (Apply to suggestions, optional for truth)
    if not is_truth:
        vram = hw.get("vram")
        if vram and vram < 12 and ctx > 32768: ctx = 32768

    return ctx, max_t, reasoning, is_truth

# --- Orchestration Domain ---

def run_universal_harness_wave():
    """
    Orchestrates the Wave 1-3 Universal Harness logic.
    """
    print("\n" + "=" * 60)
    print(" 🛠️  CK's Universal Harness v4.0 - 自動化適配中樞")
    print("=" * 60)
    
    print("[*] 正在同步專家資產 (Submodules)...")
    subprocess.run("git submodule update --init --recursive", shell=True)
    
    scripts = [
        ("purifier.py", "🧹 執行環境淨化與備份..."),
        ("detector.py", "🔍 偵測 AI CLI 環境..."),
        ("generator.py", "🤖 生成平台投影 (Projection)..."),
        ("mapper.py", "🔗 執行智慧映射 (Mapping)...")
    ]
    
    for script, desc in scripts:
        print(f"\n[*] {desc}")
        path = os.path.join(REPO_ROOT, "scripts", script)
        ok, out, err = run(f'"{sys.executable}" "{path}"')
        if not ok:
            print(f"❌ 執行 {script} 失敗: {err}")
            return False
        print(out)
        
    print("\n✅ Universal Harness 適配完成。")
    return True

def show_main_menu():
    print("=" * 60 + "\n CK's Universal Code Agent Harness - 旗艦版 (v4.0)\n" + "=" * 60)
    print("\n [1] 完整安裝 (Universal) [2] 切換模型 (Pi Only) [3] 僅投影配置 [Q] 離開")
    ans = input("\n請輸入編號 (1-3, Q): ").strip().lower()
    if ans == "1": return "full"
    if ans == "2": return "model"
    if ans == "3": return "restore"
    if ans == "q": sys.exit(0)
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["full", "model", "restore"])
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args()
    
    global AUTO_MODE
    AUTO_MODE = args.auto
    mode = args.mode or show_main_menu()
    while not mode: mode = show_main_menu()

    print(f"\n[*] 模式: {mode} | 系統: {platform.system()}")

    # Git Initialization
    run(f'git config --global --add safe.directory "{REPO_ROOT}"')
    
    # Wave 1-3: Universal Logic
    if mode in ["full", "restore"]:
        if not run_universal_harness_wave():
            sys.exit(1)

    if mode == "full":
        print("\n🔍 正在檢查核心組件...")
        # ... (rest of core check)

        for cmd in ["git", "python", "npm"]:
            if not has_command(cmd): print(f"❌ 找不到 {cmd}"); sys.exit(1)
        print("✅ 環境核心組件已就緒。")
        if has_command("pi"): run_stream("pi update")
        else: run_stream("npm install -g @mariozechner/pi-coding-agent")

    if mode in ["full", "model"]:
        models = detect_llm_services()
        if not models:
            print("[-] 未偵測到運行中的本地 LLM。將跳過模型配置。")
        else:
            print("\n發現以下模型:")
            for i, (p, m) in enumerate(models, 1): print(f"  [{i}] {m} ({p})")
            idx = int(input("請選擇模型編號 (0 跳過): ") or 0)
            if idx > 0:
                api_base, model_id = models[idx-1]
                hw = get_hardware_info()
                rec_ctx, rec_max_t, is_reasoning, found_truth = get_recommended_specs(model_id, hw, api_base=api_base, provider="ollama" if "11434" in api_base else "custom")
                
                print(f"\n  [硬體] RAM: {hw['ram'] or '??'}GB | VRAM: {hw['vram'] or '??'}GB")
                print(f"  [實測] {model_id}{' (API 實測值)' if found_truth else ''}")
                
                u_ctx = input(f"  1. Context Window [{rec_ctx}]: ").strip()
                final_ctx = int(u_ctx) if u_ctx else rec_ctx
                u_max = input(f"  2. Max Tokens     [{rec_max_t}]: ").strip()
                final_max = int(u_max) if u_max else rec_max_t
                u_res = input(f"  3. Enable Reasoning [Y/n]: ").strip().lower()
                final_res = is_reasoning if u_res == "" else (u_res == "y")

                # Update Settings
                settings = load_json(SETTINGS_PATH)
                settings["defaultModel"] = model_id
                settings["defaultProvider"] = "ollama" if "11434" in api_base else "local-server"
                if "11434" not in api_base: settings["apiBase"] = api_base
                gb = detect_git_bash()
                if gb: settings["shellPath"] = gb
                save_json(SETTINGS_PATH, settings)

                # Update Models JSON
                prov_id = settings["defaultProvider"]
                m_json = {"providers": {prov_id: {"baseUrl": api_base if prov_id != "ollama" else "http://127.0.0.1:11434", "api": "openai-completions", "apiKey": "local", "authHeader": True, "models": [{"id": model_id, "name": f"Local: {model_id}", "reasoning": final_res, "contextWindow": final_ctx, "maxTokens": final_max, "input": ["text"]}]}}}
                save_json(os.path.join(PI_CONFIG_DIR, "models.json"), m_json)
                print("✅ 已同步本地模型配置。")

    print("[*] 正在執行資產還原 (restore.py)...")
    run_stream(f'"{sys.executable}" "{os.path.join(REPO_ROOT, "scripts", "restore.py")}" --auto')
    print("\n" + "=" * 60 + "\n 完成！請執行: pi\n" + "=" * 60)

if __name__ == "__main__":
    main()
