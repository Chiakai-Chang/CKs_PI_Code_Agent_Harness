@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

REM --- 1. Find Python ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 找不到 Python。請先安裝 Python 並加入 PATH。
    pause
    exit /b 1
)

REM --- 2. Self-Elevation (if not admin) ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] 正在請求管理員權限以確保安裝順利...
    powershell -Command "Start-Process python -ArgumentList '%~dp0scripts\setup.py' -Verb RunAs"
    exit /b 0
)

REM --- 3. Launch the Brain (setup.py) ---
python "%~dp0scripts\setup.py"
pause
