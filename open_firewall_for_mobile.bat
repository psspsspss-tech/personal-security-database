@echo off
title Security Suite — Open Firewall for Mobile Access
echo.
echo  Opening Windows Firewall for Security Dashboard (port 8765)...
echo  This allows your iPhone and Android to connect.
echo.

REM Remove old rule if exists, then re-add
netsh advfirewall firewall delete rule name="Security Suite Port 8765" >nul 2>&1
netsh advfirewall firewall add rule name="Security Suite Port 8765" dir=in action=allow protocol=TCP localport=8765

if %errorlevel% == 0 (
    echo  [OK] Firewall rule added! Port 8765 is now open.
    echo.
    for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr "IPv4" ^| findstr /v "127.0.0.1"') do (
        set IP=%%a
        goto :show
    )
    :show
    set IP=%IP: =%
    echo  Your iPhone/Android URL:  http://%IP%:8765
    echo.
    echo  Open Safari on iPhone, type that URL, then:
    echo  Share button ^> Add to Home Screen ^> Add
) else (
    echo  [FAIL] Could not add firewall rule.
    echo  Please right-click this file and choose "Run as administrator"
)
echo.
pause
