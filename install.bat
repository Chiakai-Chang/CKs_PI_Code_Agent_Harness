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
REM Quote the script path (repo may live under a path with spaces), keep the
REM elevated window open (cmd /k) so errors stay visible, and pin the working
REM directory (elevated processes otherwise start in System32).
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] 正在請求管理員權限以確保安裝順利...
    powershell -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', 'chcp 65001 >nul && python \"%~dp0scripts\setup.py\"' -WorkingDirectory '%~dp0.' -Verb RunAs"
    exit /b 0
)

REM --- 3. Run Setup Brain ---
python "%~dp0scripts\setup.py"
pause
