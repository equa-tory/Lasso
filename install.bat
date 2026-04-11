@echo off
set SCRIPT_DIR=%~dp0bin

echo Adding to PATH...
setx PATH "%PATH%;%SCRIPT_DIR%"

echo Done. Restart terminal.
pause