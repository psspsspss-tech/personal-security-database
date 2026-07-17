@echo off
title Repairing Windows Component Store...
echo.
echo  =====================================================
echo    WINDOWS COMPONENT REPAIR TOOL — Security Suite
echo  =====================================================
echo.
echo  This tool will repair the corrupted Windows Component Store
echo  (DISM Error 14098) so that WSL features can be enabled.
echo.
echo  IMPORTANT: This process requires an active internet connection
echo  and can take 10-20 minutes depending on your system speed.
echo.
pause

echo.
echo  [STEP 1/2] Restoring health using DISM (downloading clean files)...
DISM.exe /Online /Cleanup-Image /RestoreHealth

echo.
echo  [STEP 2/2] Running System File Checker (SFC scan)...
SFC.exe /scannow

echo.
echo  =====================================================
echo  [FINISH] Component store repair completed!
echo.
echo  Please RESTART your PC, then run Install-Kali-External.bat again.
echo  =====================================================
echo.
pause
