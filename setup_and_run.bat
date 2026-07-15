@echo off
setlocal

echo ======================================================
echo  PrintSmith Report Server - Scheduled Watchdog Setup
echo ======================================================
echo.
echo This launcher delegates startup and updates to Windows Task Scheduler.
echo The first setup must run from an Administrator window.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_server_auto_update.ps1"

if errorlevel 1 (
    echo.
    echo Setup or startup failed. Review the message above.
    pause
)

endlocal
