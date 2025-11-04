@echo off
REM Batch file to restart the backend server

echo.
echo ========================================
echo   RESTARTING BACKEND SERVER
echo ========================================
echo.

REM Navigate to backend directory
cd /d %~dp0

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if port 8001 is in use and kill it
echo.
echo Checking port 8001...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8001" ^| findstr "LISTENING"') do (
    echo Killing existing process on port 8001...
    taskkill /F /PID %%a >nul 2>&1
    timeout /t 2 /nobreak >nul
)

REM Start the backend server
echo.
echo Starting backend server on port 8001...
echo Server will be available at: http://localhost:8001
echo Press CTRL+C to stop the server
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

pause

