@echo off
cd /d "%~dp0"
set VENV=%LOCALAPPDATA%\MarketplaceBot\venv
rem Si hay librerias nuevas en requirements.txt, las instala primero.
fc /b requirements.txt "%VENV%\requirements.txt" >nul 2>&1 || call Instalar.bat
start "" "%VENV%\Scripts\pythonw.exe" app.py
