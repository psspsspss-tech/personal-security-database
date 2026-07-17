@echo off
color 0b
title Security Command Center Manager

:menu
cls
echo =======================================================
echo          SECURITY COMMAND CENTER - MANAGER
echo =======================================================
echo.
echo   [1] Start SecurityCenter (Background)
echo   [2] Stop SecurityCenter
echo   [3] Recompile Executable (from source)
echo   [4] Sync changes to GitHub
echo   [5] Enable Auto-Start on Boot
echo   [6] Disable Auto-Start on Boot
echo   [7] Exit
echo.
set /p choice="Select an option (1-7): "

if "%choice%"=="1" goto start
if "%choice%"=="2" goto stop
if "%choice%"=="3" goto recompile
if "%choice%"=="4" goto sync
if "%choice%"=="5" goto enable_boot
if "%choice%"=="6" goto disable_boot
if "%choice%"=="7" exit

goto menu

:start
echo.
echo Starting SecurityCenter in the background...
start "" "dist\SecurityCenter.exe"
echo Done!
pause
goto menu

:stop
echo.
echo Stopping SecurityCenter...
powershell -Command "Stop-Process -Name 'SecurityCenter' -Force -ErrorAction SilentlyContinue"
echo Done!
pause
goto menu

:recompile
echo.
echo Recompiling Executable...
echo This will take about 30 seconds. Please wait...
powershell -Command "python -m PyInstaller --noconfirm --onefile --windowed --add-data 'dashboard;dashboard' --add-data 'backend;backend' --add-data 'agent.py;.' --name 'SecurityCenter' master.py"
echo Done!
pause
goto menu

:sync
echo.
echo Syncing to GitHub...
call sync_to_github.bat
pause
goto menu

:enable_boot
echo.
echo Enabling Auto-Start...
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut(\"$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\SecurityCenter.lnk\"); $Shortcut.TargetPath = \"$PWD\dist\SecurityCenter.exe\"; $Shortcut.WorkingDirectory = \"$PWD\dist\"; $Shortcut.Save()"
echo Done!
pause
goto menu

:disable_boot
echo.
echo Disabling Auto-Start...
powershell -Command "Remove-Item -Path \"$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\SecurityCenter.lnk\" -ErrorAction SilentlyContinue"
echo Done!
pause
goto menu
