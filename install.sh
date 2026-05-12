#!/usr/bin/env bash
#
# CK's Pi Code Agent Harness - Environment Manager
#
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

show_menu() {
    clear
    echo "============================================================"
    echo " CK's Pi Code Agent Harness - 管理與設定工具"
    echo "============================================================"
    echo ""
    echo "請選擇操作模式："
    echo ""
    echo "  [1] 完整安裝 / 環境檢查 (新用戶推薦)"
    echo "      - 檢查 Git/Python/Node"
    echo "      - 安裝/更新 Pi 助手"
    echo "      - 設定本地模型與智慧參數"
    echo "      - 還原所有 Skills/Rules"
    echo ""
    echo "  [2] 僅切換模型 (快速路徑)"
    echo "      - 重新掃描 Ollama/llama.cpp"
    echo "      - 重新生成 models.json 並套用"
    echo ""
    echo "  [3] 僅還原配置 (修復路徑)"
    echo "      - 僅同步 Skills 與 Rules 到 Pi 目錄"
    echo ""
    echo "  [Q] 離開"
    echo ""
    read -p "請輸入編號 (1-3, Q): " CHOICE

    case $CHOICE in
        1) full_setup ;;
        2) model_switch ;;
        3) restore_only ;;
        [Qq]) exit 0 ;;
        *) show_menu ;;
    esac
}

full_setup() {
    echo ""
    # Admin check & Self-Elevation
    if [[ $EUID -ne 0 ]]; then
        echo "[!] 目前非以 root/sudo 身分執行。"
        echo "    安裝全域套件時可能會受限。"
        echo ""
        read -p "是否嘗試使用 sudo 重新啟動以保證權限？ (y/N): " RSUDO
        if [[ "$RSUDO" =~ ^[Yy]$ ]]; then
            echo "正在請求 sudo 權限..."
            exec sudo bash "$0" "$@"
        fi
        echo "[*] 繼續以目前權限執行..."
        echo ""
    fi

    echo "[1/6] Initializing git submodules (ECC hooks)..."
    git submodule update --init --recursive || echo "[!] Submodule init failed."

    echo "[2/6] Checking Python..."
    if ! command -v python3 &> /dev/null; then
        echo "[!] python3 not found."
        exit 1
    fi

    echo "[3/6] Running full environment setup..."
    python3 "$SCRIPT_DIR/scripts/setup.py" --mode full
}

model_switch() {
    echo ""
    echo "[*] Jumping to model detection..."
    python3 "$SCRIPT_DIR/scripts/setup.py" --mode model
}

restore_only() {
    echo ""
    echo "[*] Restoring skills and extensions..."
    python3 "$SCRIPT_DIR/scripts/setup.py" --mode restore
}

show_menu
echo ""
read -n 1 -s -r -p "按任意鍵結束..."
echo ""
