@echo off
rem Abre la ventana con consola: si algo falla al arrancar, el error queda a la vista.
cd /d "%~dp0"
set VENV=%LOCALAPPDATA%\MarketplaceBot\venv
set PYTHONPATH=%~dp0src
"%VENV%\Scripts\python.exe" -m marketplace_bot
pause
