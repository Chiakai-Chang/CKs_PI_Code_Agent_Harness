#!/usr/bin/env python3
#
# CK's Pi Code Agent Harness - Unified Setup Script (v3.7)
#
# Handles:
# - Environment checks (Git, Python, Node/npm)
# - Pi installation/update prompts (streaming output)
# - Git Bash detection (Windows)
# - Local LLM service detection (Ollama, LMStudio, llama.cpp, etc.)
# - Model selection and models.json generation (v0.73+ format)
# - Writing settings.json
# - Running restore.py
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

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PI_CONFIG_DIR = os.path.join(REPO_ROOT, "pi-config")
SETTINGS_PATH = os.path.join(PI_CONFIG_DIR, "settings.json")
HARNESS_CONFIG_PATH = os.path.join(PI_CONFIG_DIR, "harness-config.json")

AUTO_MODE = False

def prompt_yes(prompt):
    if AUTO_MODE:
        return "y"
    return input(prompt).strip().lower()

# ─── Utilities ──────────────────────────────────────────────

def run(cmd, check=False):
    try:
        # Use shell=True and handle encoding for Windows
        r = subprocess.run(cmd, shell=True, capture_output=True, check=False)
        # Try cp65001 for Windows UTF-8, then fall back to system default
        try:
            stdout = r.stdout.decode('cp65001').strip()
            stderr = r.stderr.decode('cp65001').strip()
        except:
            stdout = r.stdout.decode(errors='replace').strip()
            stderr = r.stderr.decode(errors='replace').strip()
        return r.returncode == 0, stdout, stderr
    except Exception as e:
        return False, "", str(e)


def run_stream(cmd):
    """Run a command and stream its output so user sees progress."""
    print(f"  $ {cmd.strip()}")
    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
        proc.wait()
        return proc.returncode == 0
    except Exception:
        return False


def is_admin():
    try:
        if platform.system().lower() == "windows":
            try:
                import ctypes
                return bool(ctypes.windll.shell32.IsUserAnAdmin())
            except Exception:
                return False
        else:
            return os.geteuid() == 0
    except Exception:
        return False


def detect_platform():
    s = platform.system().lower()
    if s == "windows":
        return "windows"
    if s == "darwin":
        return "macos"
    if "linux" in s:
        return "linux"
    return "unknown"


def has_command(cmd):
    ok, _, _ = run(f"{cmd} --version")
    return ok


# ─── Install suggestions ───────────────────────────────────

def suggest_git(p):
    if p == "windows":
        print("  => 建議使用 winget 安裝 Git：")
        print("     winget install Git.Git")
    elif p == "macos":
        print("  => 建議使用 Homebrew 安裝 Git：")
        print("     brew install git")
    elif p == "linux":
        print("  => 建議使用套件管理器安裝 Git（範例 apt）：")
        print("     sudo apt update")
        print("     sudo apt install -y git")


def suggest_python(p):
    if p == "windows":
        print("  => 建議使用 winget 安裝 Python：")
        print("     winget install Python.Python.3.12")
    elif p == "macos":
        print("  => 建議使用 Homebrew 安裝 Python：")
        print("     brew install python")
    elif p == "linux":
        print("  => 建議使用套件管理器安裝 Python（範例 apt）：")
        print("     sudo apt update")
        print("     sudo apt install -y python3")


def suggest_node(p):
    if p == "windows":
        print("  => 建議使用 nvm-windows：")
        print("     1. 開啟瀏覽器：")
        print("        https://github.com/coreybutler/nvm-windows/releases")
        print("     2. 下載最新 nvm-setup.exe 並安裝")
        print("     3. 重新開啟終端機，執行: nvm install 22")
        print("     4. 再次執行: install.bat")
    elif p in ("macos", "linux"):
        print("  => 建議使用 nvm 安裝 Node（推薦）：")
        print("     1. curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash")
        print("     2. source ~/.bashrc")
        print("     3. nvm install 22")
        print("     4. nvm use 22")
        if p == "macos":
            print("     5. 再次執行: bash install.sh")
        else:
            print("     5. 再次執行: bash install.sh")


# ─── Git Bash detection (Windows) ──────────────────────────

def detect_git_bash(p):
    if p != "windows":
        return None
    
    # Common paths for Git Bash
    paths = [
        os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Git", "bin", "bash.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Git", "bin", "bash.exe"),
        os.path.join(os.environ.get("LocalAppData", ""), "Programs", "Git", "bin", "bash.exe"),
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    return None


# ─── Intel Arc detection (for labeling) ────────────────────

def has_intel_arc():
    # Check env vars and common oneAPI paths
    env_vars = ["ONEAPI_ROOT", "INTEL_ONEAPI_ROOT"]
    for v in env_vars:
        if os.environ.get(v):
            return True
    # Check common paths (best-effort)
    paths = [
        r"C:\Intel\oneAPI",
        r"C:\Program Files\Intel\oneAPI",
        "/opt/intel/oneapi",
        r"C:\Program Files (x86)\Intel\oneAPI",
    ]
    for p in paths:
        if os.path.exists(p):
            return True
    return False


# ─── Hardware Detection ──────────────────────────────────────

def get_hardware_info():
    """
    Gather basic RAM and VRAM info (zero-dependency).
    """
    info = {"ram": None, "vram": None}
    sys_p = platform.system().lower()

    # System RAM
    try:
        if sys_p == "windows":
            # wmic is faster than systeminfo. Using findall to grab first big number.
            ok, out, _ = run("wmic computersystem get TotalPhysicalMemory")
            if ok:
                nums = re.findall(r'\d+', out)
                if nums: info["ram"] = int(nums[0]) // (1024**3)
        elif sys_p == "macos":
            ok, out, _ = run("sysctl hw.memsize")
            if ok:
                nums = re.findall(r'\d+', out)
                if nums: info["ram"] = int(nums[0]) // (1024**3)
        else: # Linux
            with open("/proc/meminfo", "r") as f:
                content = f.read()
                match = re.search(r"MemTotal:\s+(\d+)\s+kB", content)
                if match:
                    info["ram"] = int(match.group(1)) // (1024**2)
    except: pass

    # NVIDIA VRAM
    try:
        ok, out, _ = run("nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits")
        if ok and out:
            # Might have multiple GPUs, sum them
            vrams = [int(x) for x in re.findall(r'\d+', out)]
            if vrams: info["vram"] = sum(vrams) // 1024
    except: pass

    return info


# ─── Model helper (v0.73+ models.json format) ─────────────

def fetch_ollama_metadata(model_name):
    """
    Try to fetch real metadata (like num_ctx) from Ollama API.
    """
    try:
        # Use 127.0.0.1 for stability
        url = "http://127.0.0.1:11434/api/show"
        data = json.dumps({"name": model_name}).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=3) as resp:
            body = json.loads(resp.read().decode())
            # Parse parameters string for num_ctx
            params = body.get("parameters", "")
            match = re.search(r'num_ctx\s+(\d+)', params)
            if match:
                return {"ctx": int(match.group(1))}
    except: pass
    return {}


def fetch_llamacpp_metadata(base_url):
    """
    Try to fetch n_ctx from llama.cpp /props or /slots endpoint.
    Supports root and /v1 paths, 127.0.0.1 fallback, and nested JSON.
    """
    urls = []
    clean_base = base_url.replace("/v1", "").rstrip("/")
    if "localhost" in clean_base:
        clean_base = clean_base.replace("localhost", "127.0.0.1")
        
    urls.append(f"{clean_base}/props")
    urls.append(f"{clean_base}/slots")
    
    for url in urls:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=1) as resp:
                data = json.loads(resp.read().decode())
                
                # Case /props:
                if "n_ctx" in data: return {"ctx": int(data["n_ctx"])}
                if "default_generation_settings" in data:
                    s = data["default_generation_settings"]
                    if "n_ctx" in s: return {"ctx": int(s["n_ctx"])}
                
                # Case /slots:
                if isinstance(data, list) and len(data) > 0:
                    ctx = data[0].get("n_ctx")
                    if ctx: return {"ctx": int(ctx)}
        except: pass
    return {}


def fetch_openai_compat_metadata(base_url, model_id):
    """
    Try to find extended metadata in standard OpenAI model list.
    """
    try:
        url = f"{base_url.rstrip('/')}/v1/models"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode())
            for m in data.get("data", []):
                if m.get("id") == model_id:
                    for key in ["max_model_len", "context_length", "n_ctx", "context_window"]:
                        if key in m: return {"ctx": int(m[key])}
    except: pass
    return {}


def get_recommended_specs(model_id, hw, provider=None, api_base=None):
    """
    Dynamically recommend specs. Prioritize real metadata from providers.
    """
    mid = (model_id or "").lower()
    
    # Defaults
    ctx = 8192
    max_t = 4096
    reasoning = False
    found_truth = False

    # 0. DEEP DETECTION (Priority 1: Real Metadata)
    meta = {}
    if provider == "ollama":
        meta = fetch_ollama_metadata(model_id)
    elif api_base:
        meta = fetch_llamacpp_metadata(api_base)
        if not meta:
            meta = fetch_openai_compat_metadata(api_base, model_id)
    
    if meta.get("ctx"):
        ctx = meta["ctx"]
        found_truth = True

    # 1. Detect Reasoning
    if any(k in mid for k in ["r1", "thought", "opus", "deepseek"]):
        reasoning = True
    
    # 2. Series Heuristics (Upscale if truth is too small or missing)
    if "qwen" in mid:
        reasoning = True
        if not found_truth or ctx < 32768:
            ctx = 32768 if not found_truth else max(ctx, 32768)

    # 3. Model Size Heuristics
    match = re.search(r'([0-9]+)b', mid)
    if match:
        size = int(match.group(1))
        if size >= 70 and (not found_truth or ctx < 32768):
            ctx = 32768
            max_t = 8192
        elif size >= 27 and (not found_truth or ctx < 131072):
            ctx = 131072
            max_t = 16384
    
    # 4. Special Override (Qwen 3.6)
    if "3.6" in mid and (not found_truth or ctx < 196608):
        ctx = 196608

    # 5. Hardware Safety Rail (ONLY if truth NOT found)
    if not found_truth:
        vram = hw.get("vram")
        ram = hw.get("ram")
        if vram and vram < 12 and ctx > 32768:
            ctx = 32768
        elif not vram and ram and ram < 16 and ctx > 16384:
            ctx = 8192

    return ctx, max_t, reasoning, found_truth


def probe_ollama():
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=1) as response:
            data = json.loads(response.read().decode())
            return [("ollama", m["name"]) for m in data.get("models", [])]
    except:
        return []

def probe_llama_cpp(url):
    """Deep probe for llama.cpp /props or /slots endpoint."""
    try:
        # Use 127.0.0.1 for stability
        target = url.replace("localhost", "127.0.0.1")
        target_props = target.rstrip("/") + "/props"
            
        with urllib.request.urlopen(target_props, timeout=1) as response:
            data = json.loads(response.read().decode())
            n_ctx = data.get("default_generation_settings", {}).get("n_ctx", 0)
            if not n_ctx: n_ctx = data.get("n_ctx", 0)
            
            model_path = data.get("model_path", "unknown")
            model_name = os.path.basename(model_path)
            return {"name": model_name, "ctx": n_ctx}
    except:
        # Fallback to /slots
        try:
            target_slots = url.replace("localhost", "127.0.0.1").rstrip("/") + "/slots"
            with urllib.request.urlopen(target_slots, timeout=1) as response:
                data = json.loads(response.read().decode())
                if isinstance(data, list) and len(data) > 0:
                    n_ctx = data[0].get("n_ctx", 0)
                    return {"name": "Detected Slot", "ctx": n_ctx}
        except: pass
    return None

def detect_llm_services():
    models = probe_ollama()
    
    # Common local LLM ports
    ports = [11434, 1234, 8080, 8000, 3000]
    for port in ports:
        if port == 11434: continue # Already handled by probe_ollama
        url = f"http://localhost:{port}"
        try:
            probe = probe_llama_cpp(url)
            if probe:
                models.append((url, probe["name"]))
        except:
            pass
    return models


def build_models_json(selected_provider, selected_model, selected_api_base):
    """
    Build models.json with deep truth-based detection.
    """
    hw = get_hardware_info()
    
    rec_ctx, rec_max_t, is_reasoning, found_truth = get_recommended_specs(selected_model, hw, selected_provider, selected_api_base)
    
    truth_label = " (API 實測值)" if found_truth else ""
    
    print()
    print("=" * 60)
    ram_str = f"{hw['ram']}GB" if hw['ram'] else "??GB"
    vram_str = f"{hw['vram']}GB" if hw['vram'] else "??GB"
    print(f"  [環境偵測] RAM: {ram_str} | VRAM: {vram_str}")
    print(f"  [配置模型] {selected_model}{truth_label}")
    print("-" * 60)
    print("  請確認或修改以下參數 (直接按 Enter 使用推薦值)：")
    
    try:
        user_ctx = input(f"  1. Context Window [{rec_ctx}]: ").strip()
        final_ctx = int(user_ctx) if user_ctx else rec_ctx
        
        user_max_t = input(f"  2. Max Tokens [{rec_max_t}]: ").strip()
        final_max_t = int(user_max_t) if user_max_t else rec_max_t
        
        reasoning_str = "Y" if is_reasoning else "n"
        user_reasoning = input(f"  3. Enable Reasoning/Thought [{reasoning_str}]: ").strip().lower()
        if user_reasoning == "": final_reasoning = is_reasoning
        else: final_reasoning = user_reasoning in ("y", "yes", "true")
    except:
        final_ctx, final_max_t, final_reasoning = rec_ctx, rec_max_t, is_reasoning

    # Build unique IDs
    provider_id = "local-server"
    model_label = f"Local: {selected_model}"
    if selected_provider == "ollama":
        provider_id = "ollama"
        model_label = f"Ollama: {selected_model}"

    # Detect if it's a Qwen-style thinking model
    is_qwen = "qwen" in selected_model.lower()
    compat_extra = {}
    if is_qwen and final_reasoning:
        compat_extra["thinkingFormat"] = "qwen"

    models_json = {
        "providers": {
            provider_id: {
                "baseUrl": selected_api_base,
                "api": "openai-completions",
                "apiKey": "local",
                "authHeader": True,
                "compat": {
                    "supportsDeveloperRole": False,
                    "maxTokensField": "max_tokens"
                },
                "models": [
                    {
                        "id": selected_model,
                        "name": model_label,
                        "reasoning": final_reasoning,
                        "contextWindow": final_ctx,
                        "maxTokens": final_max_t,
                        "input": ["text"],
                        "cost": {
                            "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0
                        }
                    }
                ]
            }
        }
    }

    if compat_extra:
        models_json["providers"][provider_id]["models"][0]["compat"] = compat_extra

    return models_json


# ─── Restore helper ─────────────────────────────────────────

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

def get_harness_config():
    return load_json(HARNESS_CONFIG_PATH)

def check_harness_version():
    cfg = get_harness_config()
    print(f"  [SETUP] Harness version: {cfg.get('harnessVersion', 'unknown')}")
    
    # Also check pi version
    ok, out, _ = run("pi --version")
    if ok:
        print(f"  [SETUP] 偵測到 Pi 版本: {out}")
        if "0.7" in out:
            print("  ✅ Pi 版本符合建議。")
        else:
            print("  ⚠️ 建議使用 v0.70+ 版本。")

def run_restore(git_bash, p):
    script = os.path.join(REPO_ROOT, "scripts", "restore.py")
    if not os.path.exists(script):
        print("  [!] 找不到 scripts/restore.py，跳過還原步驟。")
        return

    print("  正在執行 restore.py ...")

    python = sys.executable
    run_stream(f'"{python}" "{script}" --auto')

    print("  ✅ Restore 完成。")

    # Write harness version metadata
    harness_cfg = get_harness_config()
    version_info = {
        "harnessVersion": harness_cfg.get("harnessVersion"),
        "timestamp": "auto"
    }
    agent_dir = os.path.join(os.path.expanduser("~"), ".pi", "agent")
    version_file = os.path.join(agent_dir, "harness-version.json")
    save_json(version_file, version_info)


# ─── Main Flow Helpers ──────────────────────────────────────

def show_main_menu():
    """Flagship Main Menu for the Harness."""
    print("=" * 60)
    print(" CK's Pi Code Agent Harness - 管理與設定工具 (v3.7)")
    print("=" * 60)
    print()
    print(" 請選擇操作模式：")
    print()
    print("   [1] 完整安裝 / 環境檢查 (新用戶推薦)")
    print("       * 檢查 Git/Python/Node")
    print("       * 安裝/更新 Pi 助手")
    print("       * 設定本地模型與智慧參數")
    print("       * 還原所有 Skills/Rules")
    print()
    print("   [2] 僅切換模型 (快速路徑)")
    print("       * 重新掃描 Ollama/llama.cpp")
    print("       * 重新生成 models.json 並套用")
    print()
    print("   [3] 僅還原配置 (修復路徑)")
    print("       * 僅同步 Skills 與 Rules 到 Pi 目錄")
    print()
    print("   [Q] 離開")
    print()
    
    ans = input("請輸入編號 (1-3, Q): ").strip().lower()
    if ans == "1": return "full"
    if ans == "2": return "model"
    if ans == "3": return "restore"
    if ans in ("q", "quit", "exit"): sys.exit(0)
    return None


def init_git_harness():
    """Ensure Git trust and submodules are initialized."""
    print("[*] 正在初始化 Git 環境與子模組資產...")
    
    # 1. Add safe directory to fix 'dubious ownership' on some filesystems
    run(f'git config --global --add safe.directory "{REPO_ROOT}"')
    
    # 2. Update submodules recursively to pull in all experts
    print("    -> 正在拉取專家代理人資產 (Submodules)...")
    if not run_stream("git submodule update --init --recursive"):
        print("    [!] 子模組初始化失敗，部分專家功能可能無法使用。")


def main():
    parser = argparse.ArgumentParser(description="CK's Pi Code Agent Harness - Setup")
    parser.add_argument("--auto", action="store_true",
                        help="Non-interactive mode with sensible defaults")
    parser.add_argument("--mode", choices=["full", "model", "restore"],
                        help="Operating mode: full setup, model switch only, or restore only")
    args = parser.parse_args()

    global AUTO_MODE
    AUTO_MODE = args.auto
    mode = args.mode

    # If no mode provided, show interactive menu
    if not mode:
        while not mode:
            mode = show_main_menu()

    p = detect_platform()

    print()
    print("=" * 60)
    print(" CK's Pi Code Agent Harness – 環境與配置管理")
    print("=" * 60)
    
    mode_map = {"full": "完整環境檢查與安裝", "model": "僅切換/配置本地模型", "restore": "僅還原 Skills 與 Extensions"}
    print(f"  [模式] {mode_map.get(mode, mode)}")
    print(f"  偵測系統: {platform.system()}")
    if not is_admin():
        print("  目前非管理員/非 root（部分指令可能受限）")
    print()

    # --- Git / Submodule Phase ---
    if mode in ["full", "restore"]:
        init_git_harness()
        print()

    # --- Mode: Restore Only ---
    if mode == "restore":
        git_bash = detect_git_bash(p)
        run_restore(git_bash, p)
        return

    # --- Mode: Full (Environment Checks) ---
    if mode == "full":
        print("🔍 正在檢查核心環境...")
        
        # 1. Check Git
        if not has_command("git"):
            print("❌ 未偵測到 Git。")
            suggest_git(p)
            sys.exit(1)
        else:
            print("✅ 已偵測到 Git。")

        # 2. Check Python
        print("✅ Python 已就緒。")

        # 3. Check Node/npm
        if not has_command("node") or not has_command("npm"):
            print("❌ 未偵測到 Node.js 或 npm。")
            suggest_node(p)
            sys.exit(1)

        # Node version check
        try:
            result = subprocess.run(["node", "-v"], capture_output=True, text=True, timeout=5)
            node_version_str = (result.stdout or "").strip().lstrip("v")
            node_major = int(node_version_str.split(".")[0])
            if node_major < 20:
                print(f"❌ Node.js 版本過低 (v{node_version_str})，Pi 要求 >= 20。")
                suggest_node(p)
                sys.exit(1)
        except: pass
        print("✅ Node.js / npm 已就緒。")

        # 4. Check Pi
        if not has_command("pi"):
            print("❌ 未偵測到 pi 命令。")
            ans = prompt_yes("  是否現在安裝 Pi？ (y/N): ")
            if ans in ("y", "yes"):
                run_stream("npm install -g @mariozechner/pi-coding-agent")
            else:
                sys.exit(1)
        else:
            ans = prompt_yes("  是否更新 Pi 到最新版？ (y/N): ")
            if ans in ("y", "yes"):
                run_stream("pi update")
        
        # 4.2 Check Optional Stealth Browser (Camofox)
        if not has_command("camofox-browser"):
            print("  [選配] 偵測到未安裝 Camofox 高隱身瀏覽器。")
            ans = prompt_yes("  是否現在安裝？ (y/N) (需耗費較多空間): ")
            if ans in ("y", "yes"):
                run_stream("npm install -g camofox-browser")
        
        check_harness_version()
        print()

    # --- Mode: Full or Model (LLM Setup) ---
    if mode in ["full", "model"]:
        git_bash = detect_git_bash(p)
        if mode == "full" and git_bash:
            print(f"✅ 偵測到 Git Bash: {git_bash}")

        print("  正在掃描本地 LLM 服務...")
        agent_models_path = os.path.join(os.path.expanduser("~"), ".pi", "agent", "models.json")
        has_existing_config = os.path.exists(agent_models_path)
        
        all_models = detect_llm_services()

        selected_provider = None
        selected_model = None
        selected_api_base = None

        if not all_models:
            print("  [提示] 未偵測到運行中的本地 LLM。")
            if has_existing_config:
                print("  [資訊] 將保留您現有的配置。")
        else:
            if has_existing_config:
                print(f"  [偵測] 發現現有配置。您可以選擇一個模型來「升級/切換」。")
            
            print("  發現以下模型:")
            for i, (prov, model) in enumerate(all_models, start=1):
                label = f"API: {prov}" if prov.startswith("http") else f"Provider: {prov}"
                print(f"  [{i}] {model} ({label})")
            print("  [0] 不自動設定，保持現狀")

            try:
                choice_str = input("  請選擇模型編號: ").strip()
                choice = int(choice_str) if choice_str else 0
            except: choice = 0

            if choice != 0 and 0 < choice <= len(all_models):
                prov, model = all_models[choice - 1]
                selected_provider = "custom-openai-compatible" if prov.startswith("http") else prov
                selected_model = model
                selected_api_base = prov if prov.startswith("http") else ("http://localhost:11434" if prov == "ollama" else None)
                print(f"  已選擇: {selected_model}")
            else:
                print("  未更動模型設定。")

        # Save configs
        if selected_provider:
            # Update settings.json
            settings = load_json(SETTINGS_PATH)
            if git_bash: settings["shellPath"] = git_bash
            settings["defaultProvider"] = selected_provider
            settings["defaultModel"] = selected_model
            if selected_api_base: settings["apiBase"] = selected_api_base
            if "packages" not in settings:
                settings["packages"] = ["npm:context-mode", "npm:@tintinweb/pi-tasks"]
            save_json(SETTINGS_PATH, settings)
            print("✅ 已更新 pi-config/settings.json")

            # Update models.json
            models_data = build_models_json(selected_provider, selected_model, selected_api_base)
            if models_data:
                save_json(os.path.join(PI_CONFIG_DIR, "models.json"), models_data)
                print("✅ 已更新 pi-config/models.json")

        # Finally, run restore if in full mode or if user switched models
        if mode == "full":
            run_restore_flag = prompt_yes("  是否執行還原配置到 ~/.pi/agent？ (Y/n): ")
            if run_restore_flag not in ("n", "no"):
                run_restore(git_bash, p)
        elif selected_provider:
            # If they just switched models, we MUST restore at least the config files
            print("  正在同步新配置到 Pi 代理目錄...")
            run_restore(git_bash, p)

    print()
    print("=" * 60)
    print(" 完成！")
    print("  1. 執行: pi")
    print("  2. 確認 Skills 與模型是否如預期運作")
    print("=" * 60)

if __name__ == "__main__":
    main()
