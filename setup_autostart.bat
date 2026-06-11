@echo off
title Setup Auto-Start — Security Suite
echo.
echo  Setting up Security Suite to start automatically at Windows login...
echo.

set SCRIPT_PATH=%~dp0start.bat
set TASK_NAME=PersonalSecuritySuite

REM Remove old task if exists
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

REM Create scheduled task to run at logon (current user)
schtasks /create /tn "%TASK_NAME%" ^
  /tr "cmd /c start /min \"\" \"%SCRIPT_PATH%\"" ^
  /sc ONLOGON ^
  /rl HIGHEST ^
  /f >nul 2>&1

if %errorlevel% equ 0 (
    echo  [OK] Auto-start configured! Security Suite will launch automatically on login.
) else (
    echo  [WARN] Could not create scheduled task. Try running as Administrator.
)
echo.
echo  To disable auto-start, run:
echo    schtasks /delete /tn "%TASK_NAME%" /f
echo.
pause
