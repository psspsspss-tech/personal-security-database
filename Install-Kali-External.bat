@echo off
title Installing WSL / Kali Linux to External HDD...
echo.
echo  =====================================================
echo    EXTERNAL WSL/KALI INSTALLER — Security Suite
echo  =====================================================
echo.
echo  This tool will install Kali Linux WSL2 directly onto your
echo  external drive (e.g. D:) to save space on your C: drive.
echo.

:: Ask for drive letter
set /p target_drive="Enter your external HDD drive letter (e.g. D): "
if "%target_drive%"=="" set target_drive=D
:: Clean up target_drive to just letter
set target_drive=%target_drive:~0,1%

echo.
echo  Target Path will be: %target_drive%:\WSL\kali-linux
echo.
pause

echo.
echo  [STEP 1/5] Enabling WSL2 features...
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
wsl --set-default-version 2

echo.
echo  [STEP 2/5] Downloading and installing Kali Linux...
echo  A new terminal window will open to set up your username/password.
echo  Please complete that setup, then return to this window.
echo.
wsl --install -d kali-linux

echo.
echo  =====================================================
echo  Have you finished setting up your username/password in
echo  the Kali terminal window?
echo  =====================================================
pause

:: Ask for username they just created to configure /etc/wsl.conf
set /p wsl_user="Enter the username you just created in Kali: "

echo.
echo  [STEP 3/5] Configuring default user inside Kali...
wsl -d kali-linux -u root -- sh -c "echo '[user]' > /etc/wsl.conf && echo 'default=%wsl_user%' >> /etc/wsl.conf"

echo.
echo  [STEP 4/5] Exporting Kali to %target_drive%:\kali-linux-temp.tar...
if not exist "%target_drive%:\WSL" mkdir "%target_drive%:\WSL"
wsl --export kali-linux "%target_drive%:\kali-linux-temp.tar"

echo.
echo  [STEP 5/5] Re-locating Kali to %target_drive%:\WSL\kali-linux...
wsl --unregister kali-linux
wsl --import kali-linux "%target_drive%:\WSL\kali-linux" "%target_drive%:\kali-linux-temp.tar" --version 2

echo.
echo  Cleaning up temporary files...
del "%target_drive%:\kali-linux-temp.tar"

echo.
echo  =====================================================
echo  [OK] Kali Linux successfully installed to %target_drive%:\WSL\kali-linux!
echo.
echo   Run this command in cmd to install core pentest tools:
echo.
echo     wsl -d kali-linux -- sudo apt update
echo     wsl -d kali-linux -- sudo apt install -y kali-linux-headless
echo.
echo   You can now start the Kali terminal from the dashboard.
echo  =====================================================
echo.
pause
