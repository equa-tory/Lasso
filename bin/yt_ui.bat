@echo off
pythonw "%~dp0..\yt_ui.py" %*
if errorlevel 1 python "%~dp0..\yt_ui.py" %*
