#!/usr/bin/env python3
#
# CK's Pi Code Agent Harness - Unified Setup Script
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
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
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
            text=True
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
    candidates = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c.replace("\\", "\\\\")  # escape for JSON
    return None


# ─── Local LLM detection ───────────────────────────────────

def fetch_json_get(url):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def detect_ollama():
    data = fetch_json_get("http://localhost:11434/api/tags")
    if data and isinstance(data, dict):
        models = []
        for m in data.get("models", []):
            name = m.get("name")
            if name:
                models.append(("ollama", name))
        return models
    return []


def detect_openai_compat(base_url):
    data = fetch_json_get(f"{base_url}/v1/models")
    if data and isinstance(data, dict):
        models = []
        for m in data.get("data", []):
            mid = m.get("id")
            if mid:
                models.append((base_url.rstrip("/"), mid))
        return models
    return []


def detect_llm_services():
    all_models = []

    # Ollama
    all_models.extend(detect_ollama())

    # LMStudio / LocalAI / llama.cpp / generic OpenAI-compatible
    endpoints = [
        "http://localhost:1234",
        "http://localhost:8080",
        "http://localhost:5000",
    ]
    for url in endpoints:
        all_models.extend(detect_openai_compat(url))

    # deduplicate while preserving order
    seen = set()
    unique = []
    for p, m in all_models:
        if (p, m) not in seen:
            seen.add((p, m))
            unique.append((p, m))
    return unique


# ─── JSON helpers ───────────────────────────────────────────

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def parse_version(version_str):
    version_str = (version_str or "").strip().lstrip("vV")
    parts = []
    for segment in version_str.split("."):
        try:
            parts.append(int(segment))
        except ValueError:
            break
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def get_harness_config():
    if not os.path.exists(HARNESS_CONFIG_PATH):
        return {}
    return load_json(HARNESS_CONFIG_PATH)


def check_harness_version():
    harness_cfg = get_harness_config()
    min_recommended = harness_cfg.get("minRecommendedPiVersion", "0.73.0")
    harness_version = harness_cfg.get("harnessVersion", "unknown")

    ok, out, _ = run("pi --version")
    pi_version = None
    if ok and out.strip():
        tokens = out.strip().split()
        for t in tokens:
            if any(c.isdigit() for c in t) and ("." in t or t.startswith("v")):
                pi_version = t.strip()
                break

    if pi_version is None:
        print(f"  [SETUP] Harness version: {harness_version} (recommended Pi >= {min_recommended})")
        print("  [SETUP] 無法確認 Pi 版本，若行為異常，建議先執行: pi update")
        return

    pv = parse_version(pi_version)
    mv = parse_version(min_recommended)

    print(f"  [SETUP] Harness version: {harness_version}")
    print(f"  [SETUP] 偵測到 Pi 版本: {pi_version}")

    if pv < mv:
        print(f"  ⚠️  目前 Pi 版本低於建議版本 ({min_recommended})，部分功能可能不穩定。")
        print("     建議執行: pi update")
        ans = prompt_yes("  是否現在更新 Pi？(y/N): ")
        if ans in ("y", "yes"):
            run("pi update")
    else:
        print("  ✅ Pi 版本符合建議。")


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


# ─── Model helper (v0.73+ models.json format) ─────────────

def guess_max_tokens(model_id):
    """
    Provide a reasonable default maxTokens based on model name heuristics.
    """
    mid = (model_id or "").lower()

    # Reasoning / Large models
    if any(k in mid for k in ["qwen3.6", "qwen3_6", "qwen-3.6", "r1", "opus"]):
        return 32768
    
    if "70b" in mid:
        return 16384

    # Mid-size
    if any(k in mid for k in ["14b", "27b", "32b", "35b"]):
        return 16384

    # Standard
    return 8192


def guess_context_window(model_id):
    """
    Guess context window size.
    """
    mid = (model_id or "").lower()

    # Modern large context models
    if any(k in mid for k in ["qwen3.6", "qwen3_6", "qwen-3.6"]):
        return 196608
    
    if "qwen" in mid or "r1" in mid:
        return 131072
    
    if "llama-3.1" in mid or "llama-3.2" in mid or "llama3.1" in mid:
        return 131072

    return 8192


def build_models_json(selected_provider, selected_model, selected_api_base):
    """
    Build models.json in v0.73+ format with professional defaults.
    """
    if not selected_provider or not selected_model or not selected_api_base:
        return None

    # Derive provider ID
    if selected_provider == "ollama":
        provider_id = "ollama-local"
    else:
        # Use a more descriptive ID for OpenAI-compatible
        if "8080" in selected_api_base:
            provider_id = "llama-cpp-local"
        else:
            provider_id = "local-openai-compatible"

    # Label: add Intel Arc tag if detected
    model_label = selected_model
    if has_intel_arc():
        model_label += " (Intel Arc SYCL)"

    # Heuristics
    max_tokens = guess_max_tokens(selected_model)
    context_window = guess_context_window(selected_model)

    # Reasoning / Thinking format detection
    is_qwen = "qwen" in selected_model.lower()
    is_reasoning = any(k in selected_model.lower() for k in ["qwen", "r1", "opus", "thought"])
    
    compat_extra = {}
    if is_qwen:
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
                        "reasoning": is_reasoning,
                        "contextWindow": context_window,
                        "maxTokens": max_tokens,
                        "input": ["text"],
                        "cost": {
                            "input": 0,
                            "output": 0,
                            "cacheRead": 0,
                            "cacheWrite": 0
                        }
                    }
                ]
            }
        }
    }

    # Add thinkingFormat if detected
    if compat_extra:
        models_json["providers"][provider_id]["models"][0]["compat"] = compat_extra

    return models_json


# ─── Restore helper ─────────────────────────────────────────

def run_restore(git_bash, p):
    script = os.path.join(REPO_ROOT, "scripts", "restore.py")
    if not os.path.exists(script):
        print("  [!] 找不到 scripts/restore.py，跳過還原步驟。")
        return

    print("  正在執行 restore.py ...")

    python = sys.executable
    run_stream(f'"{python}" "{script}"')

    print("  ✅ Restore 完成。")

    # Write harness version metadata into agent dir (for future checks)
    harness_cfg = get_harness_config()
    version_info = {
        "harnessVersion": harness_cfg.get("harnessVersion"),
        "timestamp": "auto"
    }
    agent_dir = os.path.join(os.path.expanduser("~"), ".pi", "agent")
    version_file = os.path.join(agent_dir, "harness-version.json")
    save_json(version_file, version_info)


# ─── Main Flow ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="CK's Pi Code Agent Harness - Setup")
    parser.add_argument("--auto", action="store_true",
                        help="Non-interactive mode with sensible defaults (for CI / advanced users)")
    args = parser.parse_args()

    global AUTO_MODE
    AUTO_MODE = args.auto

    p = detect_platform()

    print("=" * 60)
    print(" CK's Pi Code Agent Harness – 環境檢查與設定")
    print("=" * 60)
    print(f"  偵測系統: {platform.system()}")
    if not is_admin():
        print("  目前非管理員/非 root（部分安裝指令可能需要提權）")
    print()

    # 1. Check Git
    if not has_command("git"):
        print("❌ 未偵測到 Git。")
        suggest_git(p)
        print("請安裝完成後，重新執行此腳本。\n")
        sys.exit(1)
    else:
        print("✅ 已偵測到 Git。")

    # 2. Check Python (already running, but confirm)
    print("✅ Python 已就緒。")

    # 3. Check Node/npm (require >= 20 for Pi)
    if not has_command("node") or not has_command("npm"):
        print("❌ 未偵測到 Node.js 或 npm。")
        suggest_node(p)
        print("請安裝完成並重新開啟終端機，再執行此腳本。\n")
        sys.exit(1)

    # Check Node version
    try:
        import subprocess
        result = subprocess.run(["node", "-v"], capture_output=True, text=True, timeout=5)
        node_version_str = (result.stdout or "").strip().lstrip("v")
        node_major = int(node_version_str.split(".")[0])
        if node_major < 20:
            print(f"❌ Node.js 版本過低（目前 v{node_version_str}），Pi 要求 Node >= 20。")
            suggest_node(p)
            print("請升級 Node 後重新執行此腳本。\n")
            sys.exit(1)
    except Exception:
        print("⚠️ 無法確認 Node.js 版本，若後續安裝失敗，請確認 Node >= 20。\n")

    print("✅ Node.js / npm 已就緒。")
    print()

    # 4. Check Pi (stream output so user sees progress)
    if not has_command("pi"):
        print("❌ 未偵測到 pi 命令。")
        ans = prompt_yes("  是否現在安裝 Pi？ (y/N): ")
        if ans in ("y", "yes"):
            print("  正在安裝 Pi（全域）... 以下為安裝進度，請等待...")
            ok = run_stream("npm install -g @mariozechner/pi-coding-agent")
            if not ok:
                print("  ⚠️ 安裝失敗，可能需要管理員權限。")
                if p == "windows":
                    print("     請嘗試：以系統管理員身分開啟終端機，重新執行 install.bat")
                else:
                    print("     請嘗試加上 sudo 重新執行 npm install -g @mariozechner/pi-coding-agent")
                print()
                sys.exit(1)
            print("  ✅ Pi 安裝完成。")
        else:
            print("  請手動安裝 Pi 後，重新執行此腳本。")
            print("     npm install -g @mariozechner/pi-coding-agent")
            sys.exit(1)
    else:
        ans = prompt_yes("  是否更新 Pi 到最新版？ (y/N): ")
        if ans in ("y", "yes"):
            print("  正在更新 Pi ... 以下為更新進度，請等待...")
            run_stream("pi update")
            print("  ✅ 完成。")

    # 4.1 Harness & Pi version check (non-blocking)
    check_harness_version()
    print()

    # 5. Detect Git Bash (Windows)
    git_bash = detect_git_bash(p)
    if git_bash:
        print(f"✅ 偵測到 Git Bash: {git_bash}")
    else:
        git_bash = None
        if p == "windows":
            print("⚠️ 未偵測到 Git Bash，settings.json 中的 shellPath 需手動設定。")
        print()

    # 6. Detect Local LLM
    print("  正在掃描本地 LLM 服務（Ollama / LMStudio / llama.cpp 等）...")
    all_models = detect_llm_services()

    selected_provider = None
    selected_model = None
    selected_api_base = None

    if not all_models:
        print("  [INFO] No local LLM detected.")
        print("  You can:")
        print("    - Install Ollama (recommended): https://ollama.ai")
        print("      Windows: winget install Ollama.Ollama")
        print("      macOS:   brew install ollama")
        print("      Then re-run this script to auto-configure.")
        print("    - Or configure a cloud API key later (edit pi-config/settings.json)")
        print("    - Or skip and configure manually.")
        print("  This is not required to continue.")
    else:
        print("  發現以下模型:")
        for i, (prov, model) in enumerate(all_models, start=1):
            if prov.startswith("http"):
                print(f"  [{i}] {model} (API: {prov})")
            else:
                print(f"  [{i}] {model} (Provider: {prov})")
        print("  [0] 不自動設定，稍後手動調整")

        try:
            choice = int(input("  請選擇模型編號: ").strip())
        except:
            choice = 0

        if choice != 0 and 0 < choice <= len(all_models):
            prov, model = all_models[choice - 1]
            if prov.startswith("http"):
                selected_api_base = prov
                selected_provider = "custom-openai-compatible"
            else:
                selected_provider = prov  # e.g., "ollama"
            selected_model = model
            # For ollama, set apiBase
            if selected_provider == "ollama":
                selected_api_base = "http://localhost:11434"
            print(f"  已選擇: {selected_model}")
        else:
            print("  未選擇模型，將保留原有設定或手動調整。")
    print()

    # 7. Prepare settings.json
    settings = load_json(SETTINGS_PATH)

    # shellPath
    if git_bash:
        settings["shellPath"] = git_bash

    # model
    if selected_provider:
        settings["defaultProvider"] = selected_provider
        settings["defaultModel"] = selected_model
        if selected_api_base:
            settings["apiBase"] = selected_api_base

    # ensure packages list exists
    if "packages" not in settings:
        settings["packages"] = [
            "npm:context-mode",
            "npm:@tintinweb/pi-tasks"
        ]

    save_json(SETTINGS_PATH, settings)
    print("✅ 已寫入 pi-config/settings.json")

    # 8. Generate models.json (v0.73+ format)
    if selected_provider:
        models_data = build_models_json(selected_provider, selected_model, selected_api_base)
        if models_data:
            models_json_path = os.path.join(PI_CONFIG_DIR, "models.json")
            save_json(models_json_path, models_data)
            print("✅ 已寫入 pi-config/models.json (v0.73+ 格式)")
    else:
        print("  [INFO] 未選擇模型，models.json 尚未生成。你可稍後手動調整。")

    # 9. Ask to run restore
    run_restore_flag = prompt_yes("  是否執行還原配置到 ~/.pi/agent？ (Y/n): ")
    if run_restore_flag not in ("n", "no"):
        run_restore(git_bash, p)
    else:
        print("  已跳過還原步驟。你可稍後執行: python scripts/restore.py")

    print()
    print("=" * 60)
    print(" 下一步：")
    print("  1. 執行: pi")
    print("  2. 確認 Skills、Extensions 是否正常")
    print("  3. 若需調整模型或路徑，可編輯 pi-config/settings.json 或 models.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
