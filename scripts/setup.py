#!/usr/bin/env python3
#
# CK's Pi Code Agent Harness - Unified Setup Script
#
# Handles:
# - Environment checks (Git, Python, Node/npm)
# - Pi installation/update prompts
# - Git Bash detection (Windows)
# - Local LLM service detection (Ollama, LMStudio, etc.)
# - Model selection
# - Writing settings.json, model.json
# - Running restore.sh
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

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PI_CONFIG_DIR = os.path.join(REPO_ROOT, "pi-config")
SETTINGS_PATH = os.path.join(PI_CONFIG_DIR, "settings.json")
MODEL_JSON_PATH = os.path.join(PI_CONFIG_DIR, "model.json")
HARNESS_CONFIG_PATH = os.path.join(PI_CONFIG_DIR, "harness-config.json")


# ─── Utilities ──────────────────────────────────────────────

def run(cmd, check=False):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return False, "", str(e)


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
    elif p == "macos":
        print("  => 建議使用 nvm 安裝 Node（推薦）：")
        print("     1. curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash")
        print("     2. source ~/.bashrc")
        print("     3. nvm install 22")
        print("     4. nvm use 22")
        print("     5. 再次執行: bash install.sh")
    elif p == "linux":
        print("  => 建議使用 nvm 安裝 Node（推薦，避免系統 Node 衝突）：")
        print("     1. curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash")
        print("     2. source ~/.bashrc")
        print("     3. nvm install 22")
        print("     4. nvm use 22")
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
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def parse_version(version_str):
    # Best-effort parse x.y.z from strings like "0.73.0", "v0.73.0", etc. First three numeric parts.
    version_str = (version_str or "").strip().lstrip("vV")
    parts = []
    for segment in version_str.split("."):
        try:
            parts.append(int(segment))
        except ValueError:
            # If non-numeric, stop parsing further
            break
    # Pad to (major, minor, patch)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def get_harness_config():
    if not os.path.exists(HARNESS_CONFIG_PATH):
        return {}
    return load_json(HARNESS_CONFIG_PATH)


def check_harness_version():
    # Non-blocking version check: warn if Pi version < recommended.
    harness_cfg = get_harness_config()
    min_recommended = harness_cfg.get("minRecommendedPiVersion", "0.73.0")
    harness_version = harness_cfg.get("harnessVersion", "unknown")

    # Try to detect Pi version (pi --version or similar) – best effort
    ok, out, _ = run("pi --version")
    pi_version = None
    if ok and out.strip():
        # take first token that looks version-like
        tokens = out.strip().split()
        for t in tokens:
            if any(c.isdigit() for c in t) and ("." in t or t.startswith("v")):
                pi_version = t.strip()
                break

    if pi_version is None:
        # cannot reliably detect; just inform
        print(f"  [SETUP] Harness version: {harness_version} (recommended Pi >= {min_recommended})")
        print("  [SETUP] 無法確認 Pi 版本，若行為異常，建議先執行: pi update")
        return

    # Compare versions
    pv = parse_version(pi_version)
    mv = parse_version(min_recommended)

    print(f"  [SETUP] Harness version: {harness_version}")
    print(f"  [SETUP] 偵測到 Pi 版本: {pi_version}")

    if pv < mv:
        print(f"  ⚠️  目前 Pi 版本低於建議版本 ({min_recommended})，部分功能可能不穩定。")
        print("     建議執行: pi update")
        ans = input("  是否現在更新 Pi？(y/N): ").strip().lower()
        if ans in ("y", "yes"):
            run("pi update")
    else:
        print("  ✅ Pi 版本符合建議。")


# ─── Restore helper ─────────────────────────────────────────

def run_restore(git_bash, p):
    script = os.path.join(REPO_ROOT, "scripts", "restore.sh")
    if not os.path.exists(script):
        print("  [!] 找不到 scripts/restore.sh，跳過還原步驟。")
        return

    print("  正在執行 restore.sh ...")

    if p == "windows":
        if git_bash:
            cmd = f'"{git_bash}" -c "cd \\"{REPO_ROOT}\\" && bash scripts/restore.sh"'
        else:
            # fallback; may require bash in PATH
            cmd = f"bash {script}"
        run(cmd)
    else:
        run(f"bash {script}")

    print("  ✅ Restore 完成。")

    # Write harness version metadata into agent dir (for future checks)
    harness_cfg = get_harness_config()
    version_info = {
        "harnessVersion": harness_cfg.get("harnessVersion"),
        "timestamp": "auto"  # can be enhanced if needed
    }
    agent_dir = os.path.join(os.path.expanduser("~"), ".pi", "agent")
    version_file = os.path.join(agent_dir, "harness-version.json")
    save_json(version_file, version_info)


# ─── Main Flow ──────────────────────────────────────────────

def main():
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
        # Parse major version
        node_major = int(node_version_str.split(".")[0])
        if node_major < 20:
            print(f"❌ Node.js 版本過低（目前 v{node_version_str}），Pi 要求 Node >= 20。")
            suggest_node(p)
            print("請升級 Node 後重新執行此腳本。\n")
            sys.exit(1)
    except Exception:
        # Fallback: if detection fails, still proceed (but warn)
        print("⚠️ 無法確認 Node.js 版本，若後續安裝失敗，請確認 Node >= 20。\n")

    print("✅ Node.js / npm 已就緒。")
    print()

    # 4. Check Pi
    if not has_command("pi"):
        print("❌ 未偵測到 pi 命令。")
        ans = input("  是否現在安裝 Pi？ (y/N): ").strip().lower()
        if ans in ("y", "yes"):
            print("  正在安裝 Pi（全域）...")
            ok, out, err = run("npm install -g @mariozechner/pi-coding-agent")
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
        ans = input("  是否更新 Pi 到最新版？ (y/N): ").strip().lower()
        if ans in ("y", "yes"):
            print("  正在更新 Pi ...")
            run("pi update")
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
        print("  未偵測到本地 LLM 服務或模型。你可以稍後手動調整 settings.json。")
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

    # ensure packages list exists (if not present)
    if "packages" not in settings:
        settings["packages"] = [
            "npm:context-mode",
            "npm:@tintinweb/pi-tasks"
        ]

    save_json(SETTINGS_PATH, settings)
    print("✅ 已寫入 pi-config/settings.json")

    # 8. (Optional) model.json
    if selected_provider:
        model_cfg = {
            "provider": settings.get("defaultProvider"),
            "model": settings.get("defaultModel"),
        }
        if "apiBase" in settings:
            model_cfg["apiBase"] = settings["apiBase"]
        save_json(MODEL_JSON_PATH, model_cfg)
        print("✅ 已寫入 pi-config/model.json")

    # 9. Ask to run restore
    run_restore_flag = input("  是否執行還原配置到 ~/.pi/agent？ (Y/n): ").strip().lower()
    if run_restore_flag not in ("n", "no"):
        run_restore(git_bash, p)
    else:
        print("  已跳過還原步驟。你可稍後執行: bash scripts/restore.sh")

    print()
    print("=" * 60)
    print(" 下一步：")
    print("  1. 執行: pi")
    print("  2. 確認 Skills、Extensions 是否正常")
    print("  3. 若需調整模型或路徑，可編輯 pi-config/settings.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
