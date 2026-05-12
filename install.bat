@echo off
setlocal enabledelayedexpansion

title CK's Pi Code Agent Harness - One-Click Installer

cls
echo ============================================================
echo  CK's Pi Code Agent Harness - One-Click Installer (Windows)
echo ============================================================
echo.
echo  This script will:
echo    - Check Git / Python / Node.js
echo    - Install Pi (AI coding assistant)
echo    - Apply dev skills and rules
echo    - Scan local LLM services (Ollama, etc.)
echo.
echo  It will NOT:
echo    - Collect personal data
echo    - Call external tracking APIs
echo    - Modify system environment variables
echo.
echo  Source:
echo    GitHub: https://github.com/Chiakai-Chang/CKs_PI_Code_Agent_Harness
echo    License: MIT
echo.
set /p "CONFIRM=Continue? (y/N): "
if /i not "%CONFIRM%"=="y" (
    echo Installation cancelled.
    pause
    exit /b 0
)
echo.

REM Admin check (best-effort)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Currently not running as Administrator.
    echo     Some steps (e.g., npm install -g) may require it.
    echo     If later steps fail, re-run as Administrator.
    echo.
)

REM [1/6] Init submodules
echo [1/6] Initializing git submodules (ECC hooks)...
git submodule update --init --recursive
if errorlevel 1 (
    echo [!] Submodule init failed. This is OK for first run.
    echo     ECC hooks will be unavailable until submodule is initialized.
)
echo ✅ Submodule init done.

REM [2/6] Check Python
echo [2/6] Checking Python...
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
echo ✅ Python OK.

REM [3/6] Run setup (handles Node, Pi, LLM, restore)
echo [3/6] Running environment setup...
python scripts\setup.py
if errorlevel 1 (
    echo.
    echo [!] Setup failed or exited with error.
    echo.
    echo  Possible causes:
    echo  - npm install -g requires admin:
    echo      Run install.bat as Administrator.
    echo  - Just installed Node/Python but not yet effective:
    echo      Close all terminals, reopen, then run .\install.bat
    echo  - Network or permission issues:
    echo      Try running as Administrator.
    echo.
    pause
    exit /b 1
)

echo [4/6] Environment setup complete.

REM [5/6] Fallback restore if not run inside setup.py
if exist scripts\restore.py (
    echo [5/6] If restore was not run inside setup.py, run:
    echo     python scripts\restore.py
    echo.
)

REM [6/6] Done
echo [6/6] Done!
echo.
echo  Next steps:
echo    1. Run: pi
echo    2. Confirm Skills and Extensions loaded
echo    3. If needed, adjust models in pi-config/settings.json or models.json
echo.

pause
