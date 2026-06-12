@echo off
:loop
cls
echo ======================================================
echo  PrintSmith Report Server - Auto Update Mode
echo ======================================================
echo.
echo [1/2] Checking for latest code from GitHub...
git pull origin main

if not exist "venv" (
    echo.
    echo [*] Creating virtual environment...
    python -m venv venv
)

echo.
echo [2/2] Starting Server...
echo Access at: http://localhost:8000
echo.
echo (Press Ctrl+C and then 'N' to update and restart)
echo ------------------------------------------------------
call venv\Scripts\activate
pip install -r requirements.txt
python main.py

echo.
echo Server stopped. Checking for updates and restarting in 5 seconds...
timeout /t 5
goto loop
