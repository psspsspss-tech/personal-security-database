@echo off
title Installing 24/7 Auto-Start...
echo.
echo  =======================================================
echo   Setting up Security Suite for 24/7 Auto-Start...
echo  =======================================================
echo.

set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS_FILE=%STARTUP_DIR%\SecuritySuite_Silent.vbs"

echo  [*] Creating silent startup script...
echo Set WshShell = CreateObject("WScript.Shell") > "%VBS_FILE%"
echo WshShell.Run """%~dp0Server-Loop.bat""", 0, False >> "%VBS_FILE%"

echo.
echo  =======================================================
echo  [OK] Auto-start installed!
echo.
echo   The server will now start silently in the background
echo   every time this PC boots, and will auto-restart if
echo   it crashes.
echo.
echo   To stop it manually, run: Stop-Server.bat
echo  =======================================================
echo.
pause
