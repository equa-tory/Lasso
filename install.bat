@echo off
setlocal
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
    echo  https://www.python.org/downloads/  — tick "Add Python to PATH"
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  OK %%v

:: ── Deno ──────────────────────────────────────────────────────────────────────
deno --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  Installing Deno...
    winget install DenoLand.Deno --accept-source-agreements --accept-package-agreements
) else (
    for /f "tokens=1-2" %%a in ('deno --version 2^>^&1 ^| findstr deno') do echo  OK %%a %%b
)

:: ── ffmpeg ────────────────────────────────────────────────────────────────────
if exist "%~dp0ffmpeg\ffmpeg.exe" (
    echo  OK ffmpeg in .\ffmpeg\  ^(auto-detected^)
) else (
    ffmpeg -version >nul 2>&1
    if errorlevel 1 (
        echo  Installing ffmpeg...
        winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
    ) else ( echo  OK ffmpeg in system PATH )
)

:: ── bin\yt.bat and bin\yt_ui.bat ──────────────────────────────────────────────
if not exist "%~dp0bin" mkdir "%~dp0bin"

(echo @echo off
 echo python "%%~dp0..\yt_download.py" %%*
) > "%~dp0bin\yt.bat"

(echo @echo off
 echo pythonw "%%~dp0..\yt_ui.py" %%*
 echo if errorlevel 1 python "%%~dp0..\yt_ui.py" %%*
) > "%~dp0bin\yt_ui.bat"

echo  Created bin\yt.bat and bin\yt_ui.bat

:: ── Add bin\ to user PATH (permanent, single-line PowerShell, no pipe) ────────
::    Reads only the user PATH from registry — safe, no size-limit risk.
::    -notlike '*…*' checks substring without needing Where-Object (avoids | pipe).
powershell -NoProfile -ExecutionPolicy Bypass -Command "$b=[System.IO.Path]::GetFullPath('%~dp0bin');$c=[Environment]::GetEnvironmentVariable('PATH','User');if($c -notlike ('*'+$b+'*')){[Environment]::SetEnvironmentVariable('PATH',($c+';'+$b).TrimStart(';'),'User');Write-Host '  Added to PATH.'}else{Write-Host '  Already in PATH.'}"

echo.
echo  ==========================================
echo   Done!  Open a NEW terminal window, then:
echo.
echo     yt --help          CLI
echo     yt_ui              GUI
echo.
echo   Examples:
echo     yt 1-4 v https://youtube.com/playlist?...
echo     yt 1 a https://youtu.be/...
echo     yt l a https://...   ^(sync: new only^)
echo  ==========================================
echo.
pause
