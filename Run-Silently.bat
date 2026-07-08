@echo off
cd /d "%~dp0"
title Security Suite - Starting silently...

:: Launch the crash-restart loop invisibly using pythonw (no console window)
:: We use a VBScript trick to launch Server-Loop.bat with no window
set "VBS=%TEMP%\ss_launch.vbs"
echo Set WshShell = CreateObject("WScript.Shell") > "%VBS%"
echo WshShell.Run """%~dp0Server-Loop.bat""", 0, False >> "%VBS%"
cscript //nologo "%VBS%"

echo  [OK] Security Suite is running silently in the background.
echo  (To stop it, run Stop-Server.bat)
echo.
timeout /t 3 >nul
