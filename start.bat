@echo off
echo ========================================
echo   Jarvis AI Tutor
echo ========================================
echo.

REM Check if frontend is built
if not exist "frontend\dist\index.html" (
    echo Building frontend...
    cd /d D:\ai\ai-tutor\frontend
    call npm install
    call npm run build
    if errorlevel 1 (
        echo.
        echo ERROR: Frontend build failed
        pause
        exit /b 1
    )
    echo Frontend built successfully!
    echo.
)

echo Starting Jarvis backend...
echo.
cd /d D:\ai\ai-tutor\backend
python main.py
