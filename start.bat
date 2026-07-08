@echo off
title Personal Security Suite — Launcher
color 0B

:: ─── Check for Administrator Privileges ───
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo  [!] Administrator privileges required!
    echo  Please right-click start.bat and select "Run as Administrator".
    echo.
    pause
    exit /b 1
)

echo.
echo  =======================================================
echo      Personal Security Command Center
echo  =======================================================
echo.

REM ─── Kill any old process on ports 8767 and 8768 ───
echo  [*] Checking for existing server on ports 8767 / 8768...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8767" ^| findstr "LISTENING"') do (
    echo  [*] Stopping old server (PID %%a)...
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8768" ^| findstr "LISTENING"') do (
    echo  [*] Stopping old server (PID %%a)...
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

REM ─── Check Python ───
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python is not installed or not in PATH.
    echo.
    echo  Please install Python 3.9+ from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)
echo  [OK] Python found.

REM ─── Install dependencies ───
echo  [*] Verifying Python dependencies...
pip install -r "%~dp0backend\requirements.txt" --quiet --disable-pip-version-check 2>nul
echo  [OK] Dependencies ready.

REM ─── Get local IP for display ───
set LOCAL_IP=127.0.0.1
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address" ^| findstr /v "127.0.0.1"') do (
    set LOCAL_IP=%%a
    goto :gotip
)
:gotip
set LOCAL_IP=%LOCAL_IP: =%

echo.
echo  =======================================================
echo   Dashboard URLs:
echo     This PC  :  https://localhost:8767
echo     Network  :  https://%LOCAL_IP%:8767
echo  =======================================================
echo   Scan the QR code in the dashboard to open on mobile
echo  =======================================================
echo.
echo  Press Ctrl+C to stop the server.
echo.

REM ─── Launch Flask server and open browser ───
cd /d "%~dp0backend"
timeout /t 2 /nobreak >nul
start "" "https://localhost:8767"
python server.py

pause
