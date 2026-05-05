@echo off
setlocal enabledelayedexpansion

title CK's Pi Code Agent Harness - One-Click Installer

cls
echo ============================================================
echo  CK's Pi Code Agent Harness - One-Click Installer (Windows)
echo ============================================================
echo.

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
    echo     If you installed Node or Python just now, open a new terminal and run:
    echo     .\install.bat
    pause
    exit /b 1
)

echo.
pause
