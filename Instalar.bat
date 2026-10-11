@echo off
cd /d "%~dp0"
set VENV=%LOCALAPPDATA%\MarketplaceBot\venv
if not exist "%VENV%\Scripts\python.exe" (
  echo Creando el entorno de Python...
  python -m venv "%VENV%" || (echo No encontre Python. Instalalo desde python.org y marca "Add to PATH". & pause & exit /b 1)
)
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip
"%VENV%\Scripts\python.exe" -m pip install -r requirements.txt || (echo Algo fallo al instalar. Mandame lo de arriba. & pause & exit /b 1)
rem Guardamos que version se instalo, para reinstalar solo si cambia.
copy /y requirements.txt "%VENV%\requirements.txt" >nul
echo.
echo Listo.
pause
