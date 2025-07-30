@echo off
setlocal

:: ---- CONFIGURATION ----
set OUTPUT_DIR=dist\app_bundle
set APP_ENTRY=meh_app.py
set LAUNCHER_ENTRY=meh_launcher.py

:: ---- CLEAN OLD BUILD ----
echo Cleaning old build directory...
rmdir /S /Q %OUTPUT_DIR% 2>NUL

:: ---- BUILD meh_app ----
echo.
echo Building main app (%APP_ENTRY%)...
nuitka ^
  --standalone ^
  --enable-plugin=asyncio ^
  --output-dir=%OUTPUT_DIR% ^
  %APP_ENTRY%

if errorlevel 1 (
    echo ❌ App build failed!
    exit /b 1
)

:: ---- BUILD meh_launcher ----
echo.
echo Building launcher (%LAUNCHER_ENTRY%)...
nuitka ^
  --standalone ^
  --enable-plugin=asyncio ^
  --output-dir=%OUTPUT_DIR% ^
  --nofollow-import-to=%APP_ENTRY% ^
  %LAUNCHER_ENTRY%

if errorlevel 1 (
    echo ❌ Launcher build failed!
    exit /b 1
)

echo.
echo ✅ Build complete! Output in: %OUTPUT_DIR%
endlocal
pause
