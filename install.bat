@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

REM Ensure we are in the script's directory
cd /d "%~dp0"

REM --- Git Health & Trust Check ---
git status >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] 偵測到 Git 環境異常或權限安全性警告 ^(Dubious Ownership^)。
    echo [*] 正在嘗試自動將此目錄加入信任名單...
    git config --global --add safe.directory "%~dp0"
    if %errorlevel% neq 0 (
        echo [!] 自動修復失敗。如果您使用的是外接磁碟，請手動執行：
        echo     git config --global --add safe.directory "%~dp0"
    ) else (
        echo ✅ 已自動建立 Git 信任設定。
    )
    echo.
)

title CK's Pi Code Agent Harness - Environment Manager

:menu
cls
echo ============================================================
echo  CK's Pi Code Agent Harness - 管理與設定工具
echo ============================================================
echo.
echo  請選擇操作模式：
echo.
echo    [1] 完整安裝 / 環境檢查 (新用戶推薦)
echo        - 檢查 Git/Python/Node
echo        - 安裝/更新 Pi 助手
echo        - 設定本地模型與智慧參數
echo        - 還原所有 Skills/Rules
echo.
echo    [2] 僅切換模型 (快速路徑)
echo        - 重新掃描 Ollama/llama.cpp
echo        - 重新生成 models.json 並套用
echo.
echo    [3] 僅還原配置 (修復路徑)
echo        - 僅同步 Skills 與 Rules 到 Pi 目錄
echo.
echo    [Q] 離開
echo.
set /p "CHOICE=請輸入編號 (1-3, Q): "

if "%CHOICE%"=="1" goto full_setup
if "%CHOICE%"=="2" goto model_switch
if "%CHOICE%"=="3" goto restore_only
if /i "%CHOICE%"=="q" exit /b 0
goto menu

:full_setup
echo.
REM Admin check & Self-Elevation
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 目前未以管理員身分執行。
    echo     安裝全域套件 ^(npm install -g^) 時可能會失敗。
    echo.
    set /p "RELEVATE=是否嘗試自動提權並重新啟動？ ^(y/N^): "
    if /i "!RELEVATE!"=="y" (
        powershell -Command "Start-Process '%~f0' -Verb RunAs"
        exit /b 0
    )
    echo [*] 繼續以目前權限執行...
    echo.
)

echo [1/6] Initializing git submodules (ECC hooks)...
git submodule update --init --recursive
if errorlevel 1 echo [!] Submodule init failed. 

echo [2/6] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python not found. 
    pause
    exit /b 1
)

echo [3/6] Running full environment setup...
python "%~dp0scripts\setup.py" --mode full
goto end

:model_switch
echo.
echo [*] Jumping to model detection...
python "%~dp0scripts\setup.py" --mode model
goto end

:restore_only
echo.
echo [*] Restoring skills and extensions...
python "%~dp0scripts\setup.py" --mode restore
goto end

:end
echo.
pause
