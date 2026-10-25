@echo off
cd /d "%~dp0"
set VENV=%LOCALAPPDATA%\MarketplaceBot\venv
rem Si hay librerias nuevas en requirements.txt, las instala primero.
fc /b requirements.txt "%VENV%\requirements.txt" >nul 2>&1 || call Instalar.bat
set PYTHONPATH=%~dp0src
start "" "%VENV%\Scripts\pythonw.exe" -m marketplace_bot
