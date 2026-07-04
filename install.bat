@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

REM ============================================================
REM  CK's Pi Code Agent Harness - Flagship Bootstrapper (v3.7.2)
REM  Trust / License: MIT licensed open-source project.
REM ============================================================

echo [1/3] Checking environment...
REM --- 1. Find Python ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 找不到 Python。請先安裝 Python 並加入 PATH。
    pause
    exit /b 1
)

echo [2/3] Confirming installation...
set /p confirm="Continue? (Y/n): "
if /i "!confirm!"=="n" (
    echo [*] 已取消安裝。
    exit /b 0
)

echo [3/3] Elevating privileges if required...
REM --- 2. Admin Check & Self-Elevation ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] 正在請求管理員權限以確保安裝順利...
    powershell -Command "Start-Process python -ArgumentList '%~dp0scripts\setup.py' -Verb RunAs"
    exit /b 0
)

REM --- 3. Run Setup Brain ---
python "%~dp0scripts\setup.py"
pause
