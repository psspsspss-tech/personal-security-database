@echo off
cd /d "%~dp0"

:loop
python master.py

:: If master.py crashes or exits, wait 5 seconds then restart
echo.
echo  [!] Server stopped. Restarting in 5 seconds...
timeout /t 5 >nul
goto loop
