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

# Console output contains non-ASCII status marks; legacy Windows codepages
# (e.g. cp950) crash on them when the script is run outside install.bat.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# --- Globals & Paths ---
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PI_CONFIG_DIR = os.path.join(REPO_ROOT, "pi-config")
SETTINGS_PATH = os.path.join(PI_CONFIG_DIR, "settings.json")
HARNESS_CONFIG_PATH = os.path.join(PI_CONFIG_DIR, "harness-config.json")
AUTO_MODE = False

# --- Core Utility Domain ---

def run(cmd, cwd=None):
    """Run shell command with triple-encoding fallback for cross-platform robustness.

    Always anchor to REPO_ROOT by default: the script may be launched from an
    arbitrary cwd (e.g. an elevated console starting in System32), and git
    operations must run inside the repository.
    """
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=False, check=False, cwd=cwd or REPO_ROOT)
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

def run_stream(cmd, cwd=None):
    """Run command and stream output to terminal (anchored to REPO_ROOT by default)."""
    print(f"  $ {cmd.strip()}")
    try:
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', cwd=cwd or REPO_ROOT)
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

def ask(prompt, default=""):
    """Interactive input that degrades to the default in --auto / non-tty runs."""
    if AUTO_MODE or not sys.stdin.isatty():
        print(f"{prompt}{default} (auto)")
        return default
    try:
        return input(prompt).strip()
    except EOFError:
        return default

def find_nvm_node_bin():
    """Find nvm's node binary directory if nvm is in use. Returns None if not found."""
    nvm_dir = os.path.expanduser("~/.nvm")
    node_dirs = os.path.join(nvm_dir, "versions", "node")
    if not os.path.isdir(node_dirs):
        return None
    for entry in os.listdir(node_dirs):
        candidate = os.path.join(node_dirs, entry, "bin")
        if os.path.isdir(candidate) and os.path.exists(os.path.join(candidate, "node")):
            return candidate
    return None

def maybe_heal_linux_stealth():
    """On Linux: auto-heal known systemd unit and server.js issues for stealth-recon.
    Idempotent; only acts on detected problems; best-effort (never blocks install).

    Covers the root causes documented in docs/retro/2026-07-20-camofox-linux-root-cause-fix.md:
    - systemd unit PATH missing nvm node (unit fails to start, exit 127)
    - server.js bugs in the pinned-server install (patched via camofox-server-fixes.sh)
    """
    if platform.system().lower() != "linux":
        return
    unit_path = os.path.expanduser("~/.config/systemd/user/camofox-browser.service")
    nvm_node = find_nvm_node_bin()

    # Fix 1: systemd unit PATH missing nvm node
    if os.path.isfile(unit_path) and nvm_node:
        with open(unit_path, "r", encoding="utf-8") as f:
            unit = f.read()
        if "Environment=PATH=" in unit and nvm_node not in unit:
            print("[*] systemd camofox-browser unit 的 PATH 不含 nvm node，自動修復...")
            import re
            def fix_path(m):
                old_path = m.group(1)
                return "Environment=PATH=" + nvm_node + ":" + old_path
            unit = re.sub(r"Environment=PATH=(.+)$", fix_path, unit, count=1, flags=re.MULTILINE)
            with open(unit_path, "w", encoding="utf-8") as f:
                f.write(unit)
            print("  [✓] 已加入 " + nvm_node + "，請執行: systemctl --user daemon-reload && systemctl --user restart camofox-browser.service")
        elif nvm_node in unit:
            print("[*] systemd camofox-browser unit 的 nvm node PATH 已在。")

    # Fix 2: patch server.js bugs in the pinned-server install
    server_js = os.path.expanduser("~/.camofox/pinned-server/node_modules/@askjo/camofox-browser/server.js")
    patch_script = os.path.join(REPO_ROOT, "pi-skills", "optional", "camofox-stealth", "camofox-server-fixes.sh")
    if os.path.isfile(server_js):
        needs_patch = False
        with open(server_js, "r", encoding="utf-8") as f:
            content = f.read()
        if "vdDisplay = await localVirtualDisplay.get();" not in content:
            needs_patch = True
        if "const maxAttempts = proxyPool?.launchRetries ?? 3;" not in content:
            needs_patch = True
        if "firefox_user_prefs:" not in content:
            needs_patch = True
        if "viewport: null" not in content:
            needs_patch = True
        if needs_patch:
            print("[*] 偵測到 camofox server.js 未修復的 bug，正在 patch...")
            if os.path.isfile(patch_script):
                bash = detect_git_bash() or "sh"
                if run_stream(f'"{bash}" "{patch_script}"'):
                    print("[*] server.js patch 完成。")
                else:
                    print("[-] server.js patch 失敗，請手動執行: sh " + patch_script)
            else:
                print("[-] patch 腳本未找到 (" + patch_script + ")，請手動修復，參考 docs/retro/2026-07-20-camofox-linux-root-cause-fix.md")
        else:
            print("[*] camofox server.js 已修復。")
    else:
        print("[*] pinned-server 未安裝，跳過 server.js 檢查 (recon.sh install 後再檢查)。")

def maybe_prefetch_stealth():
    """Opt-in, best-effort prefetch of the stealth-recon engine (Camoufox ~300MB).
    Offered on both fresh install and update; --auto / non-tty skips it."""
    cfg = load_json(HARNESS_CONFIG_PATH)
    camofox_ver = cfg.get("camofoxBrowserVersion", "1.11.2")  # pinned truth mirrored in recon.sh
    pf = ask("是否預抓 stealth-recon 隱身瀏覽器引擎 Camoufox (~300MB, 可選)? [y/N]: ", "n")
    if pf.strip().lower() == "y":
        print("[*] 正在預抓 stealth 引擎 (best-effort，數分鐘)...")
        # Route through recon.sh `install`, the single source of truth for the
        # pinned install. A bare `npm install @askjo/camofox-browser` is NOT
        # enough: (a) its playwright-core floats to a version whose viewport
        # payload the Camoufox juggler rejects (breaks every tab), and (b) modern
        # npm gates the engine-downloading postinstall, leaving the binary cache
        # empty. recon.sh install pins playwright-core and runs the engine fetch
        # explicitly. It installs + downloads only (no lingering server).
        recon = os.path.join(REPO_ROOT, "pi-skills", "optional", "camofox-stealth", "recon.sh")
        bash = detect_git_bash() or "sh"
        run_stream(f'"{bash}" "{recon}" install')
    else:
        print("[*] 略過 stealth 引擎預抓 (可日後執行 pi 時由 camofox-stealth 技能懶啟動)。")

def run_update():
    """One-command update: pull repo+submodules, resync config, update Pi."""
    print("[*] 正在更新 Harness 與子模組 (git pull)...")
    run_stream("git pull --recurse-submodules")
    restore_script = os.path.join(REPO_ROOT, "scripts", "restore.py")
    print("[*] 正在重新同步配置 (restore --auto，冪等、保留自訂)...")
    run_stream(f'"{sys.executable}" "{restore_script}" --auto')
    if has_command("pi"):
        print("[*] 正在更新 Pi 本體與擴充 (pi update --all)...")
        run_stream("pi update --all")
    else:
        print("[*] 未偵測到 pi，略過。裝好後可自行執行: pi update --all")
    maybe_prefetch_stealth()
    maybe_heal_linux_stealth()
    print("\n" + "=" * 60 + "\n 更新完成！請執行: pi\n" + "=" * 60)

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

    # 5. Scale output cap with the final context. Thinking models spend their
    #    reasoning inside the output budget, so a large-context model stuck at
    #    the 4096 default gets long responses truncated mid-answer ("maximum
    #    output token limit"). Ceiling 32768 keeps a runaway local model bounded.
    max_t = max(max_t, min(ctx // 8, 32768))

    return ctx, max_t, reasoning, is_truth

# --- Orchestration Domain ---

def show_main_menu():
    print("=" * 60 + "\n CK's Pi Code Agent Harness - 管理與設定工具 (v3.7.2)\n" + "=" * 60)
    print("\n [1] 完整安裝 [2] 切換模型 [3] 僅還原配置 [4] 更新 [Q] 離開")
    ans = input("\n請輸入編號 (1-4, Q): ").strip().lower()
    if ans == "1": return "full"
    if ans == "2": return "model"
    if ans == "3": return "restore"
    if ans == "4": return "update"
    if ans == "q": sys.exit(0)
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["full", "model", "restore", "update"])
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args()
    
    global AUTO_MODE
    AUTO_MODE = args.auto
    mode = args.mode
    if not mode and (AUTO_MODE or not sys.stdin.isatty()):
        mode = "restore"  # safe non-interactive default
    while not mode: mode = show_main_menu()

    print(f"\n[*] 模式: {mode} | 系統: {platform.system()}")

    # Git Initialization
    run(f'git config --global --add safe.directory "{REPO_ROOT}"')
    if mode == "update":
        run_update()
        return
    if mode in ["full", "restore"]:
        print("[*] 正在拉取專家資產 (Submodules)...")
        run_stream("git submodule update --init --recursive")

    if mode == "full":
        print("🔍 正在檢查核心組件...")
        # Python is running this script; only external tools need checking.
        # (Checking "python" breaks macOS/Linux where only "python3" exists.)
        for cmd in ["git", "npm"]:
            if not has_command(cmd): print(f"❌ 找不到 {cmd}"); sys.exit(1)
        print("✅ 環境核心組件已就緒。")
        # Fresh installs use the new canonical scope (@mariozechner/* is
        # deprecated and frozen at 0.73.1). Existing installs migrate via
        # `pi update`, whose self-update handles the scope rename.
        if has_command("pi"): run_stream("pi update")
        else: run_stream("npm install -g @earendil-works/pi-coding-agent")

        # Optional stealth-recon engine prefetch (opt-in, best-effort, --auto skips).
        maybe_prefetch_stealth()
        maybe_heal_linux_stealth()

    if mode in ["full", "model"]:
        local_models = detect_llm_services()
        print("\n請選擇模型提供商 (Model Provider):")
        print("  [1] 偵測到的本地 LLM (如 Ollama / llama.cpp)")
        print("  [2] Anthropic (Claude 雲端服務)")
        print("  [3] Google (Gemini 雲端服務)")
        print("  [4] OpenAI (ChatGPT 雲端服務)")
        print("  [5] OpenRouter (聚合雲端服務)")
        print("  [6] 自訂 OpenAI 相容伺服器 (如 DeepSeek, LM Studio, vLLM)")
        print("  [0] 暫不設定 / 保留目前設定")
        
        provider_choice = ask("請輸入提供商編號 [0]: ", "0") or "0"
        
        if provider_choice == "1":
            if not local_models:
                print("[-] 未偵測到本地 LLM (No LLM detected)。請手動輸入本地 API Base (如 http://127.0.0.1:11434):")
                api_base = input("API Base URL: ").strip()
                if api_base:
                    model_id = input("請輸入本地 Model ID: ").strip()
                    if model_id:
                        local_models = [(api_base, model_id)]
            
            if local_models:
                print("\n發現以下本地模型:")
                for i, (p, m) in enumerate(local_models, 1): print(f"  [{i}] {m} ({p})")
                idx = int(input("請選擇模型編號 (0 跳過): ") or 0)
                if 0 < idx <= len(local_models):
                    api_base, model_id = local_models[idx-1]
                    hw = get_hardware_info()
                    rec_ctx, rec_max_t, is_reasoning, found_truth = get_recommended_specs(model_id, hw, api_base=api_base, provider="ollama" if "11434" in api_base else "custom")
                    
                    print(f"\n  [硬體] RAM: {hw['ram'] or '??'}GB | VRAM: {hw['vram'] or '??'}GB")
                    print(f"  [實測] {model_id}{' (API 實測值)' if found_truth else ''}")
                    
                    u_ctx = input(f"  1. Context Window [{rec_ctx}]: ").strip()
                    final_ctx = int(u_ctx) if u_ctx else rec_ctx
                    u_max = input(f"  2. Max Tokens     [{rec_max_t}]: ").strip()
                    final_max = int(u_max) if u_max else rec_max_t
                    res_hint = "Y/n" if is_reasoning else "y/N"
                    u_res = input(f"  3. Enable Reasoning [{res_hint}]: ").strip().lower()
                    final_res = is_reasoning if u_res == "" else (u_res == "y")

                    # Update Settings
                    settings = load_json(SETTINGS_PATH)
                    settings["defaultModel"] = model_id
                    settings["defaultProvider"] = "ollama" if "11434" in api_base else "local-server"
                    if "11434" not in api_base: settings["apiBase"] = api_base
                    elif "apiBase" in settings: del settings["apiBase"]
                    save_json(SETTINGS_PATH, settings)

                    # Update Models JSON
                    prov_id = settings["defaultProvider"]
                    m_json = {"providers": {prov_id: {"baseUrl": api_base if prov_id != "ollama" else "http://127.0.0.1:11434", "api": "openai-completions", "apiKey": "local", "authHeader": True, "models": [{"id": model_id, "name": f"Local: {model_id}", "reasoning": final_res, "contextWindow": final_ctx, "maxTokens": final_max, "input": ["text"]}]}}}
                    save_json(os.path.join(PI_CONFIG_DIR, "models.json"), m_json)
                    print("✅ 已同步本地模型配置。")
            else:
                print("[-] 跳過本地模型配置。")

        elif provider_choice == "2":
            print("\n常見 Anthropic 模型:")
            print("  [1] claude-sonnet-4-5 (預設推薦)")
            print("  [2] claude-haiku-4-5")
            print("  [3] claude-opus-4-1")
            print("  [4] 自訂輸入")
            m_choice = ask("請選擇模型 [1]: ", "1") or "1"
            if m_choice == "1": model_id = "claude-sonnet-4-5"
            elif m_choice == "2": model_id = "claude-haiku-4-5"
            elif m_choice == "3": model_id = "claude-opus-4-1"
            else: model_id = ask("請輸入 Model ID: ")
            
            if model_id:
                settings = load_json(SETTINGS_PATH)
                settings["defaultModel"] = model_id
                settings["defaultProvider"] = "anthropic"
                if "apiBase" in settings: del settings["apiBase"]
                save_json(SETTINGS_PATH, settings)
                print(f"✅ 已設定預設模型為: {model_id} (Provider: anthropic)")
                print("⚠️  請記得在系統環境變數中設定 ANTHROPIC_API_KEY。")

        elif provider_choice == "3":
            print("\n常見 Google Gemini 模型:")
            print("  [1] gemini-2.5-flash (預設推薦)")
            print("  [2] gemini-2.5-pro")
            print("  [3] 自訂輸入")
            m_choice = ask("請選擇模型 [1]: ", "1") or "1"
            if m_choice == "1": model_id = "gemini-2.5-flash"
            elif m_choice == "2": model_id = "gemini-2.5-pro"
            else: model_id = ask("請輸入 Model ID: ")
            
            if model_id:
                settings = load_json(SETTINGS_PATH)
                settings["defaultModel"] = model_id
                settings["defaultProvider"] = "google"
                if "apiBase" in settings: del settings["apiBase"]
                save_json(SETTINGS_PATH, settings)
                print(f"✅ 已設定預設模型為: {model_id} (Provider: google)")
                print("⚠️  請記得在系統環境變數中設定 GEMINI_API_KEY。")

        elif provider_choice == "4":
            print("\n常見 OpenAI 模型:")
            print("  [1] gpt-5 (預設推薦)")
            print("  [2] gpt-5-mini")
            print("  [3] gpt-4o")
            print("  [4] 自訂輸入")
            m_choice = ask("請選擇模型 [1]: ", "1") or "1"
            if m_choice == "1": model_id = "gpt-5"
            elif m_choice == "2": model_id = "gpt-5-mini"
            elif m_choice == "3": model_id = "gpt-4o"
            else: model_id = ask("請輸入 Model ID: ")
            
            if model_id:
                settings = load_json(SETTINGS_PATH)
                settings["defaultModel"] = model_id
                settings["defaultProvider"] = "openai"
                if "apiBase" in settings: del settings["apiBase"]
                save_json(SETTINGS_PATH, settings)
                print(f"✅ 已設定預設模型為: {model_id} (Provider: openai)")
                print("⚠️  請記得在系統環境變數中設定 OPENAI_API_KEY。")

        elif provider_choice == "5":
            model_id = ask("請輸入 OpenRouter Model ID (如 anthropic/claude-sonnet-4.5): ")
            if model_id:
                settings = load_json(SETTINGS_PATH)
                settings["defaultModel"] = model_id
                settings["defaultProvider"] = "openrouter"
                if "apiBase" in settings: del settings["apiBase"]
                save_json(SETTINGS_PATH, settings)
                print(f"✅ 已設定預設模型為: {model_id} (Provider: openrouter)")
                print("⚠️  請記得在系統環境變數中設定 OPENROUTER_API_KEY。")

        elif provider_choice == "6":
            api_base = ask("請輸入相容 API 的 Base URL (如 https://api.deepseek.com/v1): ")
            model_id = ask("請輸入 Model ID (如 deepseek-chat): ")
            api_key = ask("請輸入 API Key (或者留空改以環境變數帶入): ")
            
            if api_base and model_id:
                settings = load_json(SETTINGS_PATH)
                settings["defaultModel"] = model_id
                settings["defaultProvider"] = "custom-openai"
                if "apiBase" in settings: del settings["apiBase"]
                save_json(SETTINGS_PATH, settings)
                
                # Write to models.json for custom provider
                m_json = {"providers": {"custom-openai": {"baseUrl": api_base, "api": "openai-completions", "apiKey": api_key or "YOUR_API_KEY", "authHeader": True, "models": [{"id": model_id, "name": f"Custom: {model_id}", "contextWindow": 32768, "maxTokens": 4096, "input": ["text"]}]}}}
                save_json(os.path.join(PI_CONFIG_DIR, "models.json"), m_json)
                print(f"✅ 已設定自訂 OpenAI 相容服務為預設。")

    profile = "standard"
    if mode in ["full", "restore"]:
        print("\n請選擇安裝的技能設定檔 (Skill Profile):")
        print("  [1] minimal (僅 Core 核心 + Caveman 極簡)")
        print("  [2] standard (Core + Superpowers + Karpathy 軟體工程常用, 推薦)")
        ans_profile = ask("請輸入設定檔編號 [2]: ", "2")
        if ans_profile == "1":
            profile = "minimal"
        else:
            profile = "standard"

    # Unconditionally detect and set Git Bash shell path on Windows
    # (written to the gitignored pi-config/settings.json, never to the template)
    gb = detect_git_bash()
    if gb:
        settings = load_json(SETTINGS_PATH)
        settings["shellPath"] = gb
        save_json(SETTINGS_PATH, settings)
        print(f"[*] 已自動設定 Windows Git Bash 路徑: {gb}")

    restore_script = os.path.join(REPO_ROOT, "scripts", "restore.py")
    if mode == "model":
        # Model switching must not reinstall skills or force a profile change
        print("[*] 正在同步模型配置 (restore.py --config-only)...")
        run_stream(f'"{sys.executable}" "{restore_script}" --auto --config-only')
    else:
        print("[*] 正在執行資產還原 (restore.py)...")
        run_stream(f'"{sys.executable}" "{restore_script}" --auto --profile {profile}')
    print("\n" + "=" * 60 + "\n 完成！請執行: pi\n" + "=" * 60)

if __name__ == "__main__":
    main()
