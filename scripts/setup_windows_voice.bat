@echo off
REM Setup script for Windows Voice Control
REM Created: 2025-07-14

echo ====================================
echo Windows Voice Control Setup
echo ====================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from python.org
    pause
    exit /b 1
)

echo Installing required packages...
pip install SpeechRecognition requests pyaudio

echo.
echo Setup complete!
echo.
echo To use Windows voice control with WSL:
echo.
echo 1. Make sure your orchestrator is running in WSL:
echo    wsl -e bash -c "cd /path/to/autonomy && docker-compose up orchestrator"
echo.
echo 2. Find your WSL2 IP address:
echo    wsl hostname -I
echo.
echo 3. Update WSL_IP in windows_voice_sender.py if needed
echo.
echo 4. Run the voice control:
echo    python windows_voice_sender.py
echo.
pause