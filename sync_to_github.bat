@echo off
setlocal
echo =======================================================
echo   Syncing Security Command Center to GitHub
echo =======================================================
echo.

:: Check if git is installed
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed or not in your PATH.
    echo Please install Git from https://git-scm.com/ and try again.
    pause
    exit /b
)

:: Get current date and time for commit message
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a:%%b)
set COMMIT_MSG=Auto-sync: %mydate% %mytime%

echo [1/3] Adding changes to Git...
git add .

echo [2/3] Committing changes...
git commit -m "%COMMIT_MSG%"

echo [3/3] Pushing to GitHub...
git push origin main

if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] All changes pushed to GitHub!
) else (
    echo.
    echo [ERROR] Failed to push. Make sure your GitHub URL is set up correctly.
)

echo.
pause
