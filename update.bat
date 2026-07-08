@echo off
chcp 65001 > nul

REM ============================================================
REM  CK's Pi Code Agent Harness - Updater
REM  Trust / License: MIT licensed open-source project.
REM ============================================================

echo [1/1] Updating (git pull + restore + pi update)...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 找不到 Python。請先安裝 Python 並加入 PATH。
    pause
    exit /b 1
)

python "%~dp0scripts\setup.py" --mode update
pause
