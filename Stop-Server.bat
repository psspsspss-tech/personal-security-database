@echo off
cd /d "%~dp0"

:: Check for administrative permissions
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo  =======================================================
    echo   [!] Elevation Required
    echo   Requesting Administrator privileges...
    echo  =======================================================
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

title Security Suite - Stopping...
echo.
echo  =======================================================
echo   Stopping Security Suite...
echo  =======================================================
echo.

:: 1. Remove auto-start VBS if present
set "VBS_FILE=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\SecuritySuite_Silent.vbs"
if exist "%VBS_FILE%" (
    echo  [*] Disabling auto-start...
    del /f /q "%VBS_FILE%" >nul 2>&1
    echo  [OK] Auto-start disabled.
)

:: 2. Kill the loop bat processes
echo  [*] Terminating background loop processes...
powershell -Command "Get-CimInstance Win32_Process -Filter \"CommandLine like '%%Server-Loop.bat%%' or CommandLine like '%%Run-Silently.bat%%'\" | ForEach-Object { Stop-Process $_.ProcessId -Force }" >nul 2>&1

:: 3. Kill python / node
echo  [*] Terminating Python and Node processes...
taskkill /F /IM pythonw.exe /T >nul 2>&1
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM node.exe /T >nul 2>&1

:: 4. Free ports 8767 and 8766
echo  [*] Releasing network ports...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8767 " ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8766 " ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

echo.
echo  =======================================================
echo  [OK] Security Suite fully stopped.
echo  =======================================================
echo.
pause
