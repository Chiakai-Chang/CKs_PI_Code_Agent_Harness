@echo off
setlocal enabledelayedexpansion

title CK's Pi Code Agent Harness - One-Click Installer

cls
echo ============================================================
echo  CK's Pi Code Agent Harness - One-Click Installer (Windows)
echo ============================================================
echo.

REM Admin check (best-effort)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 目前不是以管理員身分執行。
    echo     部分安裝（例如 npm install -g）可能需要管理員權限。
    echo     若後續提示失敗，請以管理員重新執行此批次檔。
    echo.
    echo     方式：
    echo       1. 滑鼠右鍵 install.bat
    echo       2. 選擇「以系統管理員身分執行」
    echo.
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python not found. Please install Python first:
    echo     winget install Python.Python.3.12
    echo.
    echo     After installation, open a new terminal and run:
    echo     .\install.bat
    echo.
    pause
    exit /b 1
)

REM Run setup script
python scripts\setup.py
if errorlevel 1 (
    echo.
    echo [!] Setup failed or exited with error.
    echo.
    echo 可能原因與建議：
    echo  - npm install -g 需要管理員權限：
    echo      請以管理員重新執行此批次檔。
    echo  - 剛安裝 Node / Python 但尚未生效：
    echo      請關閉所有終端機，重新開啟後再執行 .\install.bat
    echo  - 網路或權限問題：
    echo      嘗試以管理員身分執行。
    echo.
    pause
    exit /b 1
)

REM Fallback restore if not run inside setup.py
if exist scripts\restore.py (
    echo.
    echo [INFO] If restore was not run inside setup.py, run:
    echo     python scripts\restore.py
    echo.
)

pause
