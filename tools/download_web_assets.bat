@echo off
setlocal

:: ===[ Configuration ]===
set "HTMX_VERSION=1.9.10"

set "HTMX_URL=https://unpkg.com/htmx.org@%HTMX_VERSION%/dist/htmx.min.js"

set "CSS_PATH=src\midi_event_handler\web\static\css"
set "JS_PATH=src\midi_event_handler\web\static\js"

:: ===[ Create folders ]===
echo.
echo [._.] Creating static directories...
mkdir "%CSS_PATH%" 2>nul
mkdir "%JS_PATH%" 2>nul

:: ===[ Download HTMX ]===
echo.
echo [._.] Downloading HTMX v%HTMX_VERSION%...
curl -L -o "%JS_PATH%\htmx.min.js" %HTMX_URL%

:: ===[ Done ]===
echo.
echo [*o*] HTMX downloaded successfully!
echo       CSS: %CSS_PATH%
echo       JS : %JS_PATH%
pause
