@echo off
setlocal EnableDelayedExpansion
title Security Suite - Advanced Manager
color 0A

:: ─── Robust UAC Elevation Check ───
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo.
    echo  [!] Requesting Administrator Privileges...
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B
)

:: Ensure working directory is correct after elevation
cd /d "%~dp0"

:menu
cls
echo.
echo  =======================================================
echo                 SECURITY SUITE MANAGER
echo  =======================================================
echo.
echo   [1] Start Server (Interactive)
echo   [2] Start Server (Background / Hidden)
echo   [3] Stop Server (Kill all instances)
echo   [4] Enable Auto-Start on Boot
echo   [5] Disable Auto-Start on Boot
echo   [6] Re-install Dependencies
echo   [0] Exit
echo.
echo  =======================================================
set /p choice=" Select an option: "

if "%choice%"=="1" goto :start_interactive
if "%choice%"=="2" goto :start_background
if "%choice%"=="3" goto :stop_server
if "%choice%"=="4" goto :enable_autostart
if "%choice%"=="5" goto :disable_autostart
if "%choice%"=="6" goto :install_deps
if "%choice%"=="0" exit

goto :menu

:start_interactive
cls
echo  [*] Checking for old server instances...
call :kill_ports
echo  [*] Starting server...
start "" "https://127.0.0.1:8767"
cd /d "%~dp0backend"
python server.py
pause
goto :menu

:start_background
cls
echo  [*] Starting server in background...
call :kill_ports
cd /d "%~dp0backend"
:: Start using pythonw to hide console window
start "" pythonw server.py
echo  [OK] Server is now running silently in the background!
start "" "https://127.0.0.1:8767"
timeout /t 2 >nul
goto :menu

:stop_server
cls
echo  [*] Stopping all Security Suite servers...
call :kill_ports
:: Also kill any hidden pythonw processes in case they are lingering
taskkill /F /IM pythonw.exe >nul 2>&1
echo  [OK] Servers stopped.
pause
goto :menu

:enable_autostart
cls
echo  [*] Adding Security Suite to Windows Startup...
set "RUN_PATH=C:\Windows\System32\cmd.exe /c cd /d ^^^"%~dp0backend^^^" ^& pythonw server.py"
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "PersonalSecuritySuite" /t REG_SZ /d "%RUN_PATH%" /f >nul
echo  [OK] Auto-Start enabled! The server will run silently on boot.
pause
goto :menu

:disable_autostart
cls
echo  [*] Removing Security Suite from Windows Startup...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "PersonalSecuritySuite" /f >nul 2>&1
echo  [OK] Auto-Start disabled!
pause
goto :menu

:install_deps
cls
echo  [*] Installing/Updating Python dependencies...
cd /d "%~dp0backend"
pip install -r requirements.txt
echo  [OK] Done!
pause
goto :menu

:kill_ports
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8767" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8768" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
exit /b
