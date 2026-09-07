@echo off
REM ============================================================================
REM iValue PRISM - Windows One-Click Environment Setup Launcher
REM Runs setup_prism.ps1 with execution policy bypass
REM ============================================================================
title iValue PRISM - Environment Setup
cd /d "%~dp0"

echo ============================================================================
echo Starting iValue PRISM Automated Environment Setup...
echo ============================================================================

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_prism.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================================================
    echo [ERROR] Setup encountered an issue. Please review the errors above.
    echo ============================================================================
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Setup completed successfully! Press any key to exit.
pause
