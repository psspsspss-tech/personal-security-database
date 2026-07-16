@echo off
title Installing Kali Linux WSL2...
echo.
echo  =====================================================
echo    KALI LINUX WSL2 INSTALLER — Security Suite
echo  =====================================================
echo.
echo  This will enable WSL2 and install Kali Linux.
echo  Your PC will need to RESTART once after step 1.
echo.
echo  [STEP 1/3] Enabling WSL2 features...
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

echo.
echo  [STEP 2/3] Setting WSL2 as default...
wsl --set-default-version 2

echo.
echo  [STEP 3/3] Installing Kali Linux...
wsl --install -d kali-linux

echo.
echo  =====================================================
echo  [OK] Kali Linux installed!
echo.
echo   After Kali sets up your username/password,
echo   run this to install core tools:
echo.
echo     wsl -d kali-linux -- sudo apt update
echo     wsl -d kali-linux -- sudo apt install -y kali-linux-headless
echo.
echo   Then restart your Security Suite dashboard.
echo  =====================================================
echo.
pause
