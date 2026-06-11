@echo off
setlocal EnableDelayedExpansion
title YouTube Downloader — Setup

echo.
echo  ==========================================
echo   YouTube Downloader — Windows Setup
echo  ==========================================
echo.

:: ── Python ────────────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found.
    echo  Download: https://www.python.org/downloads/
    echo  Tick "Add Python to PATH" during install.
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  OK %%v

:: ── Deno ──────────────────────────────────────────────────────────────────────
deno --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  Installing Deno (JS runtime required by yt-dlp)...
    winget install DenoLand.Deno --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo  WARNING: Deno install failed. Try manually: winget install DenoLand.Deno
    )
) else (
    for /f "tokens=1" %%v in ('deno --version 2^>^&1') do echo  OK Deno %%v
)

:: ── ffmpeg ────────────────────────────────────────────────────────────────────
if exist "%~dp0ffmpeg\ffmpeg.exe" (
    echo  OK ffmpeg found in .\ffmpeg\  ^(will be used automatically^)
) else (
    ffmpeg -version >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  ffmpeg not found. Installing via winget...
        winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
        if errorlevel 1 echo  WARNING: Install manually or put ffmpeg.exe in .\ffmpeg\
    ) else (
        echo  OK ffmpeg found in system PATH
    )
)

:: ── Create bin\yt.bat if missing ──────────────────────────────────────────────
if not exist "%~dp0bin" mkdir "%~dp0bin"
if not exist "%~dp0bin\yt.bat" (
    (
        echo @echo off
        echo python "%%~dp0..\yt_download.py" %%*
    ) > "%~dp0bin\yt.bat"
    echo  Created bin\yt.bat
)

:: ── Add bin\ to user PATH permanently ────────────────────────────────────────
set "BIN=%~dp0bin"
if "%BIN:~-1%"=="\" set "BIN=%BIN:~0,-1%"

powershell -NoProfile -Command ^
  "$cur = [Environment]::GetEnvironmentVariable('PATH','User');" ^
  "if ($cur -notlike '*%BIN%*') {" ^
  "  [Environment]::SetEnvironmentVariable('PATH', $cur + ';%BIN%', 'User');" ^
  "  Write-Host '  Added to PATH: %BIN%'" ^
  "} else {" ^
  "  Write-Host '  PATH already contains bin\'" ^
  "}"

echo.
echo  ==========================================
echo   Setup complete!
echo.
echo   Open a NEW terminal window and type:
echo     yt --help
echo.
echo   Examples:
echo     yt 1-4 v https://youtube.com/playlist?list=...
echo     yt 1 a https://youtu.be/...
echo     yt          ^(interactive mode^)
echo  ==========================================
echo.
pause
