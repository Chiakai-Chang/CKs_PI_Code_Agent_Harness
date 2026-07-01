@echo off
if "%~1" == "" (
    echo Usage: switch-profile [minimal^|standard^|full]
    exit /b 1
)
python "%~dp0scripts/restore.py" --auto --profile %1
