@echo off
echo [1/3] Fetching latest code from GitHub...
git pull origin main

if not exist "venv" (
    echo [2/3] Creating virtual environment...
    python -m venv venv
)

echo [2/3] Activating environment and updating libraries...
call venv\Scripts\activate
pip install -r requirements.txt

echo [3/3] Starting PrintSmith Report Server...
echo Access at: http://localhost:8000
python main.py
pause
