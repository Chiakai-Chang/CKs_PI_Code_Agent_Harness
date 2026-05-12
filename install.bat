@echo off
setlocal enabledelayedexpansion

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
python scripts\setup.py --mode full
goto end

:model_switch
echo.
echo [*] Jumping to model detection...
python scripts\setup.py --mode model
goto end

:restore_only
echo.
echo [*] Restoring skills and extensions...
python scripts\setup.py --mode restore
goto end

:end
echo.
pause
